(() => {
  const byId = (id) => document.getElementById(id);
  let config = null;

  async function loadConfig() {
    const response = await fetch("./node-core-client.json", { cache: "no-store" });
    if (!response.ok) throw new Error("No se pudo leer node-core-client.json.");
    config = await response.json();
    if (!config.node_api_url || !config.node_id || !config.repository) {
      throw new Error("La configuración del cliente está incompleta. Exporta el cliente desde Node Core OS.");
    }
    byId("github-account").textContent = config.github_account || "No informado";
    byId("repository").textContent = config.repository;
    byId("node-id").textContent = config.node_id;
    byId("connection").textContent = "Cliente configurado para " + config.node_api_url;
  }

  byId("record-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!config) return;
    const button = byId("submit");
    button.disabled = true;
    byId("result").textContent = "Enviando información al nodo…";
    const fields = {
      display_name: byId("display-name").value.trim(),
      message: byId("message").value.trim()
    };
    try {
      const response = await fetch(config.node_api_url.replace(/\/$/, "") + "/api/github/records", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fields })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || data.detail || "El nodo rechazó el registro.");
      byId("result").textContent = "Registro recibido por el nodo. ID: " + data.record_id;
      byId("record-form").reset();
    } catch (error) {
      byId("result").textContent = "No se pudo enviar: " + error.message;
    } finally {
      button.disabled = false;
    }
  });

  loadConfig().catch((error) => {
    byId("connection").textContent = "Configuración no disponible: " + error.message;
  });
})();
