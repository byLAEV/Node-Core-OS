  const byId = (id) => document.getElementById(id);
  const text = (id, value) => { byId(id).textContent = value == null || value === "" ? "No informado" : String(value); };
  async function refreshStatus() {
    byId("refresh").disabled = true;
    byId("updated").textContent = "Consultando el runtime local…";
    try {
      const response = await fetch("/api/status", { cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || data.error || "Falló la consulta de estado.");
      byId("runtime-state").textContent = "Conectado";
      text("web-address", "127.0.0.1:" + data.web_port);
      byId("runtime-dot").className = "dot ok";
      const k = data.kubo;
      const states = {
        running: "EN EJECUCIÓN",
        not_installed: "NO INSTALADO",
        not_initialized: "NO INICIALIZADO",
        not_responding: "NO RESPONDE / DETENIDO"
      };
      byId("kubo-state").textContent = states[k.state] || "DESCONOCIDO";
      byId("kubo-dot").className = "dot " + (k.running ? "ok" : (k.installed && k.initialized ? "bad" : ""));
      text("kubo-installed", k.installed ? "Sí" : "No");
      text("kubo-initialized", k.initialized ? "Sí" : "No");
      text("kubo-peer", k.peer_id);
      text("kubo-version", k.version);
      text("kubo-api", k.api);
      text("kubo-repo", k.repo_path);
      const detail = byId("kubo-detail");
      if (k.detail) { detail.hidden = false; detail.textContent = k.detail; }
      else { detail.hidden = true; detail.textContent = ""; }
      byId("updated").textContent = "Última actualización: " + new Date().toLocaleString() + " · Datos leídos del runtime local.";
    } catch (error) {
      byId("runtime-state").textContent = "No disponible";
      byId("runtime-dot").className = "dot bad";
      byId("kubo-state").textContent = "Falló la consulta de estado";
      byId("kubo-dot").className = "dot bad";
      byId("updated").textContent = "Error: " + error.message;
    } finally {
      byId("refresh").disabled = false;
    }
  }
  byId("refresh").addEventListener("click", refreshStatus);
  refreshStatus();
