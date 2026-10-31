"use strict";
(async () => {
  const status=document.getElementById("status"), button=document.getElementById("submit");
  const response=await fetch("./node-core-client.json",{cache:"no-store"});
  if(!response.ok) throw new Error("No se encontró node-core-client.json. Exporta el cliente desde Node Core BIOS.");
  const config=await response.json();
  if(config.schema!=="node-core-os/github-pages-client/v1"||!config.record_encryption?.public_jwk) throw new Error("Configuración de cliente inválida.");
  document.getElementById("owner").textContent="Repositorio: "+config.repository+" · Pool: "+config.pool_id;
  document.getElementById("version").textContent="v"+config.client_version;
  const enc=new TextEncoder(), b64=bytes=>btoa(String.fromCharCode(...new Uint8Array(bytes)));
  function setStatus(message,kind){status.textContent=message;status.className=kind||"";}
  async function encryptRecord(fields){
    const id=crypto.randomUUID(), record={schema:"node-core-os/personal-identity-record/v1",record_id:id,created_at_utc:new Date().toISOString(),consent_given:true,fields};
    const aes=await crypto.subtle.generateKey({name:"AES-GCM",length:256},true,["encrypt"]), raw=await crypto.subtle.exportKey("raw",aes), nonce=crypto.getRandomValues(new Uint8Array(12));
    const keyId=config.record_encryption.key_id, aad=enc.encode("node-core-os/personal-identity-envelope/v1|"+id+"|"+keyId);
    const ciphertext=await crypto.subtle.encrypt({name:"AES-GCM",iv:nonce,additionalData:aad},aes,enc.encode(JSON.stringify(record)));
    const publicKey=await crypto.subtle.importKey("jwk",config.record_encryption.public_jwk,{name:"RSA-OAEP",hash:"SHA-256"},false,["encrypt"]);
    const wrapped=await crypto.subtle.encrypt({name:"RSA-OAEP"},publicKey,raw);
    return {schema:"node-core-os/personal-identity-envelope/v1",record_id:id,created_at_utc:record.created_at_utc,encryption_key_id:keyId,algorithm:"RSA-OAEP-256+A256GCM",wrapped_key:b64(wrapped),nonce:b64(nonce),ciphertext:b64(ciphertext)};
  }
  async function github(token,path,options={}){
    const r=await fetch("https://api.github.com"+path,{...options,headers:{"Accept":"application/vnd.github+json","Authorization":"Bearer "+token,"X-GitHub-Api-Version":"2022-11-28",...(options.body?{"Content-Type":"application/json"}:{})}});
    if(!r.ok) throw new Error("GitHub API HTTP "+r.status+" al guardar el registro.");
    return r.status===204?null:r.json();
  }
  button.addEventListener("click",async()=>{
    button.disabled=true;
    try{
      if(!window.isSecureContext||!crypto.subtle) throw new Error("Se requiere HTTPS y WebCrypto.");
      const token=document.getElementById("token").value.trim();
      if(!token) throw new Error("Introduce el token limitado al repositorio.");
      if(!document.getElementById("consent").checked) throw new Error("Se requiere consentimiento explícito.");
      const fields={full_name:document.getElementById("full_name").value.trim(),preferred_name:document.getElementById("preferred_name").value.trim(),contact_email:document.getElementById("contact_email").value.trim(),notes:document.getElementById("notes").value.trim()};
      if(!fields.full_name) throw new Error("El nombre que deseas registrar es obligatorio.");
      for(const value of Object.values(fields)) if(value.length>4096) throw new Error("Un campo supera el máximo permitido.");
      const user=await github(token,"/user");
      if(String(user.login).toLowerCase()!==String(config.owner_login).toLowerCase()) throw new Error("El token no pertenece al propietario configurado.");
      const repo=await github(token,"/repos/"+config.repository);
      if(String(repo.owner.login).toLowerCase()!==String(config.owner_login).toLowerCase()) throw new Error("El propietario del repositorio no coincide.");
      const envelope=await encryptRecord(fields), bytes=enc.encode(JSON.stringify(envelope,null,2)+"\n");
      let binary="";for(const byte of bytes)binary+=String.fromCharCode(byte);
      const path="records/"+envelope.record_id+".json";
      await github(token,"/repos/"+config.repository+"/contents/"+path,{method:"PUT",body:JSON.stringify({message:"node-core: add encrypted identity record "+envelope.record_id,content:btoa(binary),branch:config.default_branch})});
      for(const id of ["full_name","preferred_name","contact_email","notes","token"])document.getElementById(id).value="";
      document.getElementById("consent").checked=false;
      setStatus("Registro cifrado y guardado. El nodo propietario puede sincronizarlo desde Node Core BIOS → Identity Profile → GitHub Identity Pool.","ok");
    }catch(error){setStatus(error.message||"No se pudo registrar el documento.","error");}
    finally{button.disabled=false;}
  });
})().catch(error=>{const status=document.getElementById("status");if(status){status.textContent=error.message;status.className="error";}});
