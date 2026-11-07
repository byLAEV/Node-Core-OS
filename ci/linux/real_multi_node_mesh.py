#!/usr/bin/env python3
"""Independent Linux VM participant for the Node Core OS real mesh campaign."""
import argparse, base64, json, os, socket, subprocess, sys, threading, time, uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

LOCK=threading.RLock(); NODES={}; SIGNATURES={}; EXPECTED=0; RUN_ID=""; MANIFEST=None
REGISTRY_PORT=8765; P2P_PORT=46000

def user_only():
    if os.geteuid()==0: raise SystemExit("Must run as normal Linux user, never root.")

def api(url, value=None):
    data=None if value is None else json.dumps(value).encode()
    req=Request(url,data=data,headers={"Content-Type":"application/json"} if data else {},method="POST" if data else "GET")
    with urlopen(req,timeout=15) as r: return json.loads(r.read(2*1024*1024).decode())

def wait(fn,seconds,label):
    end=time.monotonic()+seconds; last=None
    while time.monotonic()<end:
        try:
            value=fn()
            if value:return value
        except Exception as exc:last=str(exc)
        time.sleep(2)
    raise RuntimeError("Timeout: "+label+"; "+str(last))

def respond(h,status,value):
    raw=json.dumps(value).encode(); h.send_response(status)
    h.send_header("Content-Type","application/json"); h.send_header("Content-Length",str(len(raw)))
    h.end_headers(); h.wfile.write(raw)

class Registry(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args): print("REGISTRY "+fmt%args,flush=True)
    def do_GET(self):
        with LOCK:
            if self.path=="/health":return respond(self,200,{"ok":True})
            if self.path=="/roster":return respond(self,200,{"count":len(NODES),"nodes":list(NODES.values())})
            if self.path=="/manifest":
                global MANIFEST
                if len(NODES)!=EXPECTED:return respond(self,409,{"ok":False})
                if MANIFEST is None:
                    from node_core.p2p.presence_manifest import create_manifest_body
                    members=[{"node_id":x["node_id"],"public_key":x["public_key"]} for x in NODES.values()]
                    MANIFEST=create_manifest_body(members,epoch=int(RUN_ID),created_at=int(time.time()))
                return respond(self,200,{"body":MANIFEST})
            if self.path=="/signatures":return respond(self,200,{"count":len(SIGNATURES),"signatures":list(SIGNATURES.values())})
        respond(self,404,{"ok":False})
    def do_POST(self):
        n=int(self.headers.get("Content-Length","0"))
        if not 1<=n<=2*1024*1024:return respond(self,413,{"ok":False})
        try:v=json.loads(self.rfile.read(n).decode())
        except Exception:return respond(self,400,{"ok":False})
        with LOCK:
            if self.path=="/register":
                if not isinstance(v,dict) or set(v)!={"node_index","node_id","public_key","certificate_pem","rsa_public_key_pem","host","port"}:return respond(self,400,{"ok":False})
                i=v["node_index"]
                if type(i)!=int or not 0<=i<EXPECTED or v["port"]!=P2P_PORT:return respond(self,400,{"ok":False})
                if any(x["node_id"]==v["node_id"] and k!=str(i) for k,x in NODES.items()):return respond(self,409,{"ok":False})
                NODES[str(i)]=v;return respond(self,200,{"ok":True})
            if self.path=="/signature":
                if not isinstance(v,dict) or set(v)!={"node_id","signature"}:return respond(self,400,{"ok":False})
                if v["node_id"] not in {x["node_id"] for x in NODES.values()} or v["node_id"] in SIGNATURES:return respond(self,409,{"ok":False})
                SIGNATURES[v["node_id"]]=v;return respond(self,200,{"ok":True})
        respond(self,404,{"ok":False})

def main():
    global EXPECTED,RUN_ID
    p=argparse.ArgumentParser();p.add_argument("--index",type=int,required=True);p.add_argument("--count",type=int,required=True);p.add_argument("--run-id",required=True);a=p.parse_args()
    if not 3<=a.count<=200 or not 0<=a.index<a.count:raise SystemExit("Node count/index invalid.")
    user_only();data=Path(os.environ["NODE_CORE_DATA_DIR"]);app=data/"app"
    if not app.is_dir():raise RuntimeError("Node Core OS not installed: "+str(app))
    sys.path.insert(0,str(app))
    from node_core.identity.node_identity import NodeIdentityStore
    from node_core.p2p.presence_manifest import sign_manifest,verify_manifest
    from node_core.p2p.secure_messaging import NodeRSAIdentityStore
    from node_core.p2p.service import NodePeerService
    from node_core.p2p.tls_transport import NodeTLSTransport
    EXPECTED,RUN_ID=a.count,a.run_id
    if a.index==0:
        srv=ThreadingHTTPServer(("0.0.0.0",REGISTRY_PORT),Registry)
        threading.Thread(target=srv.serve_forever,daemon=True).start()
        print("RENDEZVOUS_READY",flush=True)
    identity=NodeIdentityStore(data);meta=identity.initialize();tls=NodeTLSTransport(identity);cert=tls.ensure_certificate()
    rsa=NodeRSAIdentityStore(identity);rsa_meta=rsa.initialize()
    ip=subprocess.run(["tailscale","ip","-4"],check=True,capture_output=True,text=True).stdout.strip().splitlines()[0]
    base=f"http://ncore-{a.run_id}-0:{REGISTRY_PORT}"
    own={"node_index":a.index,"node_id":meta["node_id"],"public_key":meta["public_key"],
      "certificate_pem":base64.b64encode(cert).decode(),"rsa_public_key_pem":base64.b64encode(rsa.public_key_pem()).decode(),"host":ip,"port":P2P_PORT}
    wait(lambda:api(base+"/health").get("ok"),240,"coordinator");api(base+"/register",own)
    roster=wait(lambda:(lambda x:x if x["count"]==a.count else None)(api(base+"/roster")),900,"all VMs")["nodes"]
    roster=sorted(roster,key=lambda x:x["node_index"])
    if len({x["node_id"] for x in roster})!=a.count:raise RuntimeError("Duplicate node IDs.")
    manifest=api(base+"/manifest");api(base+"/signature",sign_manifest(identity,manifest["body"]))
    signatures=wait(lambda:(lambda x:x if x["count"]==a.count else None)(api(base+"/signatures")),900,"all Ed25519 signatures")
    verified=verify_manifest(manifest["body"],signatures["signatures"])
    if not verified["unanimous"] or verified["node_count"]!=a.count:raise RuntimeError("Unanimous manifest verification failed.")
    peers=[x for x in roster if x["node_index"]!=a.index]
    certs={x["node_id"]:base64.b64decode(x["certificate_pem"]) for x in peers}
    keys={x["node_id"]:base64.b64decode(x["rsa_public_key_pem"]) for x in peers}
    inbox=[];guard=threading.Lock()
    def receive(peer,msg_id,text):
        with guard:inbox.append({"sender_node_id":peer["node_id"],"message_id":msg_id,"text":text})
    service=NodePeerService(identity,tls,certs,host="0.0.0.0",port=P2P_PORT,timeout_seconds=20,
      rsa_identity_store=rsa,trusted_rsa_public_keys=keys,on_message=receive);service.start()
    sent=[]
    for j in sorted({(a.index+1)%a.count,(a.index+2)%a.count}):
        target=roster[j];nid=target["node_id"]
        client=NodePeerService(identity,tls,{nid:certs[nid]},timeout_seconds=20,rsa_identity_store=rsa,trusted_rsa_public_keys={nid:keys[nid]})
        payload=f"NODE_CORE_MESH|run={a.run_id}|from={a.index}|to={j}|nonce={uuid.uuid4().hex}"
        ack=wait(lambda:client.send_secure_message(target["host"],target["port"],nid,keys[nid],payload),180,f"message {a.index}->{j}")
        if ack.get("status")!="accepted" or ack.get("receiver_node_id")!=nid:raise RuntimeError("Invalid signed receipt.")
        sent.append({"target_index":j,"target_node_id":nid,"message_id":ack["message_id"]})
    expected={roster[(a.index-1)%a.count]["node_id"],roster[(a.index-2)%a.count]["node_id"]}
    wait(lambda:len({x["sender_node_id"] for x in inbox}&expected)==2,180,"inbound messages")
    service.stop()
    with guard:received=list(inbox)
    if not expected.issubset({x["sender_node_id"] for x in received}):raise RuntimeError("Missing inbound peer messages.")
    outdir=Path(os.environ["RUNNER_TEMP"])/"node-core-mesh-evidence";outdir.mkdir(parents=True,exist_ok=True)
    evidence={"schema":"node-core-real-linux-mesh-v1","run_id":a.run_id,"node_index":a.index,"expected_nodes":a.count,
      "node_id":meta["node_id"],"public_key":meta["public_key"],"tailscale_ipv4":ip,"os_release":Path("/etc/os-release").read_text(),
      "uid":os.getuid(),"hostname":socket.gethostname(),"manifest":verified,"manifest_signatures":len(signatures["signatures"]),
      "direct_messages_sent":sent,"direct_messages_received":received,"p2p_listener":{"host":"0.0.0.0","port":P2P_PORT,"mutual_tls":True},
      "installation_data_dir":str(data),"rsa_public_key_sha256":rsa_meta["public_key_sha256"],"finished_at":datetime.now(timezone.utc).isoformat()}
    target=outdir/f"node-{a.index:03d}.json";target.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n");os.chmod(target,0o600)
    print(f"NODE_PASS index={a.index} id={meta['node_id']} sent={len(sent)} received={len(received)} unanimous=true",flush=True)

if __name__=="__main__":main()
