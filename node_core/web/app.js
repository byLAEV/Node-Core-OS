  const byId = (id) => document.getElementById(id);
  const text = (id, value) => { byId(id).textContent = value == null || value === "" ? "Not reported" : String(value); };
  async function refreshStatus() {
    byId("refresh").disabled = true;
    byId("updated").textContent = "Querying local runtime…";
    try {
      const response = await fetch("/api/status", { cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || data.error || "Status request failed.");
      byId("runtime-state").textContent = "Loaded";
      byId("runtime-dot").className = "dot ok";
      const k = data.kubo;
      const states = {
        running: "RUNNING",
        not_installed: "NOT INSTALLED",
        not_initialized: "NOT INITIALIZED",
        not_responding: "NOT RESPONDING / NOT RUNNING"
      };
      byId("kubo-state").textContent = states[k.state] || "UNKNOWN";
      byId("kubo-dot").className = "dot " + (k.running ? "ok" : (k.installed && k.initialized ? "bad" : ""));
      text("kubo-installed", k.installed ? "Yes" : "No");
      text("kubo-initialized", k.initialized ? "Yes" : "No");
      text("kubo-peer", k.peer_id);
      text("kubo-version", k.version);
      text("kubo-api", k.api);
      text("kubo-repo", k.repo_path);
      const detail = byId("kubo-detail");
      if (k.detail) { detail.hidden = false; detail.textContent = k.detail; }
      else { detail.hidden = true; detail.textContent = ""; }
      byId("updated").textContent = "Last updated: " + new Date().toLocaleString() + " · Values are read from the local runtime.";
    } catch (error) {
      byId("runtime-state").textContent = "Unavailable";
      byId("runtime-dot").className = "dot bad";
      byId("kubo-state").textContent = "Status query failed";
      byId("kubo-dot").className = "dot bad";
      byId("updated").textContent = "Error: " + error.message;
    } finally {
      byId("refresh").disabled = false;
    }
  }
  byId("refresh").addEventListener("click", refreshStatus);
  refreshStatus();
