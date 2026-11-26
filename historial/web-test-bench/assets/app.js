"use strict";

const owner = "byLAEV";
const repo = "Node-Core-OS";
const workflows = [
  { name: "Integración continua", file: "ci.yml" },
  { name: "Instalador E2E", file: "installer-e2e.yml" },
  { name: "Pruebas P2P de tres nodos", file: "three-independent-ubuntu-p2p-e2e.yml" }
];

const statusEl = document.getElementById("run-status");
const listEl = document.getElementById("workflow-runs");
const refreshButton = document.getElementById("refresh-results");

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function stateLabel(run) {
  if (run.status !== "completed") return "En curso";
  if (run.conclusion === "success") return "Correcto";
  if (run.conclusion === "failure") return "Falló";
  if (run.conclusion === "cancelled") return "Cancelado";
  if (run.conclusion === "skipped") return "Omitido";
  return run.conclusion || "Finalizado";
}

function badgeClass(run) {
  if (run.status !== "completed") return "run-badge badge-pending";
  if (run.conclusion === "success") return "run-badge badge-success";
  if (run.conclusion === "failure") return "run-badge badge-failure";
  return "run-badge badge-pending";
}

function formatDate(value) {
  if (!value) return "Fecha no disponible";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Fecha no disponible";
  return new Intl.DateTimeFormat("es-CR", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "America/Costa_Rica"
  }).format(date) + " (Costa Rica)";
}

async function loadWorkflow(workflow) {
  const endpoint = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow.file}/runs?per_page=4`;
  const response = await fetch(endpoint, {
    headers: { Accept: "application/vnd.github+json" }
  });
  if (!response.ok) {
    throw new Error(`${workflow.name}: la API de GitHub respondió HTTP ${response.status}`);
  }
  const data = await response.json();
  return (data.workflow_runs || []).map(run => ({ ...run, workflowLabel: workflow.name }));
}

function renderRuns(runs) {
  listEl.replaceChildren();
  if (!runs.length) {
    statusEl.textContent = "No se devolvieron ejecuciones. Abre GitHub Actions para revisar los workflows.";
    return;
  }

  for (const run of runs) {
    const item = makeElement("article", "run-item");
    const details = makeElement("div");
    const title = makeElement("h3", "", run.name || run.workflowLabel);
    const meta = makeElement(
      "p",
      "run-meta",
      `${run.workflowLabel} · Ejecución #${run.run_number} · ${formatDate(run.updated_at || run.created_at)} · rama ${run.head_branch || "desconocida"} · ${String(run.head_sha || "").slice(0, 7)}`
    );
    const link = makeElement("a", "", "Ver ejecución ↗");
    link.href = run.html_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    details.append(title, meta, link);
    const badge = makeElement("span", badgeClass(run), stateLabel(run));
    item.append(details, badge);
    listEl.append(item);
  }
  statusEl.textContent = `Se muestran ${runs.length} ejecuciones recientes. El estado procede de la API pública de GitHub; las fechas se muestran en hora de Costa Rica.`;
}

async function refresh() {
  refreshButton.disabled = true;
  refreshButton.textContent = "Actualizando…";
  statusEl.textContent = "Consultando ejecuciones públicas…";
  listEl.replaceChildren();
  try {
    const responses = await Promise.allSettled(workflows.map(loadWorkflow));
    const failures = responses.filter(item => item.status === "rejected");
    const runs = responses
      .filter(item => item.status === "fulfilled")
      .flatMap(item => item.value)
      .sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at));

    if (!runs.length) {
      throw new Error(failures.map(item => item.reason.message).join("; ") || "No hay resultados disponibles.");
    }
    renderRuns(runs);
    if (failures.length) {
      statusEl.textContent += ` Algunos resultados no pudieron cargarse: ${failures.map(item => item.reason.message).join("; ")}.`;
    }
  } catch (error) {
    statusEl.textContent = `No se pudieron cargar los resultados: ${error.message} Usa los enlaces directos a los workflows.`;
  } finally {
    refreshButton.disabled = false;
    refreshButton.textContent = "Actualizar resultados";
  }
}

refreshButton.addEventListener("click", refresh);
refresh();
