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

  const menuDetail = byId("menu-detail");
  const menuDescriptions = {
    bios: ["Node Core BIOS", "El submenú BIOS aún no está conectado. No se ejecuta ninguna operación desde este botón."],
    core: ["Node Core", "El menú Core aún no está conectado. Las operaciones de almacenamiento y contenido se añadirán usando el runtime existente."],
    blog: ["My Life / Node Blog", "El menú de blog aún no está conectado. No se modifica ni crea contenido en esta etapa."],
    apps: ["Applications", "El menú de aplicaciones aún no está conectado. No se ejecuta código de aplicaciones desde el navegador."]
  };

  function renderNetwork(data) {
    menuDetail.replaceChildren();
    const title = document.createElement("h3");
    title.textContent = "Network / Nodes — Kubo / IPFS";
    menuDetail.appendChild(title);
    const status = document.createElement("p");
    status.textContent = data.kubo_running ? "Kubo: EN EJECUCIÓN" : "Kubo: NO EN EJECUCIÓN";
    menuDetail.appendChild(status);
    const peerId = document.createElement("p");
    peerId.textContent = "ID del nodo: " + (data.peer_id || "No informado");
    menuDetail.appendChild(peerId);
    const count = document.createElement("p");
    count.textContent = "Pares conectados directamente: " + data.peer_count;
    menuDetail.appendChild(count);
    const note = document.createElement("p");
    note.className = "notice";
    note.textContent = "El recuento muestra solo pares conectados directamente; no representa todos los nodos de IPFS.";
    menuDetail.appendChild(note);
    if (data.detail) {
      const detail = document.createElement("p");
      detail.textContent = data.detail;
      menuDetail.appendChild(detail);
    }
    const listTitle = document.createElement("h4");
    listTitle.textContent = "Pares conectados";
    menuDetail.appendChild(listTitle);
    if (data.connected_peers.length === 0) {
      const empty = document.createElement("p");
      empty.textContent = "Kubo no reporta pares conectados directamente.";
      menuDetail.appendChild(empty);
    } else {
      const list = document.createElement("ul");
      for (const peer of data.connected_peers) {
        const item = document.createElement("li");
        item.textContent = peer;
        list.appendChild(item);
      }
      menuDetail.appendChild(list);
    }
  }

  async function openMenu(view) {
    if (view === "refresh") {
      await refreshStatus();
      menuDetail.replaceChildren();
      const title = document.createElement("h3");
      title.textContent = "Estado actualizado";
      const message = document.createElement("p");
      message.textContent = "Se volvió a consultar el estado de Kubo. Esta acción no inicia ni detiene servicios.";
      menuDetail.append(title, message);
      return;
    }
    if (view === "network") {
      menuDetail.textContent = "Consultando el estado de red de Kubo…";
      try {
        const response = await fetch("/api/network/kubo", { cache: "no-store" });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || data.error || "Consulta de red fallida.");
        renderNetwork(data);
      } catch (error) {
        menuDetail.replaceChildren();
        const title = document.createElement("h3");
        title.textContent = "No se pudo consultar la red";
        const message = document.createElement("p");
        message.textContent = error.message;
        menuDetail.append(title, message);
      }
      return;
    }
    const description = menuDescriptions[view];
    if (description) {
      menuDetail.replaceChildren();
      const title = document.createElement("h3");
      title.textContent = description[0];
      const message = document.createElement("p");
      message.textContent = description[1];
      menuDetail.append(title, message);
    }
  }

  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => openMenu(button.dataset.view));
  });

  byId("start-kubo").addEventListener("click", async () => {
    const accepted = window.confirm(
      "¿Iniciar Kubo / IPFS con la configuración actual de Node Core OS? " +
      "Si el repositorio no está inicializado, Kubo puede inicializarlo. " +
      "La operación se ejecutará como el usuario actual de Termux, sin root ni sudo."
    );
    if (!accepted) return;

    const button = byId("start-kubo");
    button.disabled = true;
    byId("updated").textContent = "Iniciando Kubo / IPFS; esperando a que responda la API local…";
    try {
      const response = await fetch("/api/kubo/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm: true }),
        cache: "no-store"
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || data.error || "No se pudo iniciar Kubo.");
      await refreshStatus();
      byId("updated").textContent = data.message + " · Estado verificado por el runtime local.";
      if (data.kubo && data.kubo.detail) {
        byId("updated").textContent += " " + data.kubo.detail;
      }
    } catch (error) {
      byId("updated").textContent = "Error al iniciar Kubo: " + error.message;
    } finally {
      button.disabled = false;
    }
  });

  byId("refresh").addEventListener("click", refreshStatus);
  refreshStatus();
