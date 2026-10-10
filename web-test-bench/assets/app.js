"use strict";

const owner = "byLAEV";
const repo = "Node-Core-OS";
const workflows = [
  { name: "GNU/Linux terminal CI", file: "ci.yml" },
  { name: "Installer end-to-end", file: "installer-e2e.yml" }
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
  if (run.status !== "completed") return "In progress";
  if (run.conclusion === "success") return "Success";
  if (run.conclusion === "failure") return "Failure";
  if (run.conclusion === "cancelled") return "Cancelled";
  return run.conclusion || "Completed";
}

function badgeClass(run) {
  if (run.status !== "completed") return "run-badge badge-pending";
  if (run.conclusion === "success") return "run-badge badge-success";
  if (run.conclusion === "failure") return "run-badge badge-failure";
  return "run-badge badge-pending";
}

function formatDate(value) {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC"
  }).format(date) + " UTC";
}

async function loadWorkflow(workflow) {
  const endpoint = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow.file}/runs?per_page=4`;
  const response = await fetch(endpoint, {
    headers: { Accept: "application/vnd.github+json" }
  });
  if (!response.ok) {
    throw new Error(`${workflow.name}: GitHub API returned HTTP ${response.status}`);
  }
  const data = await response.json();
  return (data.workflow_runs || []).map(run => ({ ...run, workflowLabel: workflow.name }));
}

function renderRuns(runs) {
  listEl.replaceChildren();
  if (!runs.length) {
    statusEl.textContent = "No workflow runs were returned. Open GitHub Actions to inspect the workflows.";
    return;
  }

  for (const run of runs) {
    const item = makeElement("article", "run-item");
    const details = makeElement("div");
    const title = makeElement("h3", "", run.name || run.workflowLabel);
    const meta = makeElement(
      "p",
      "run-meta",
      `${run.workflowLabel} · Run #${run.run_number} · ${formatDate(run.updated_at || run.created_at)} · ${run.head_branch || "branch unknown"} · ${String(run.head_sha || "").slice(0, 7)}`
    );
    const link = makeElement("a", "", "View run ↗");
    link.href = run.html_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    details.append(title, meta, link);
    const badge = makeElement("span", badgeClass(run), stateLabel(run));
    item.append(details, badge);
    listEl.append(item);
  }
  statusEl.textContent = `Showing ${runs.length} recent runs. Status is supplied by the public GitHub Actions API; timestamps are displayed in UTC.`;
}

async function refresh() {
  refreshButton.disabled = true;
  refreshButton.textContent = "Refreshing…";
  statusEl.textContent = "Loading public workflow runs…";
  listEl.replaceChildren();
  try {
    const responses = await Promise.allSettled(workflows.map(loadWorkflow));
    const failures = responses.filter(item => item.status === "rejected");
    const runs = responses
      .filter(item => item.status === "fulfilled")
      .flatMap(item => item.value)
      .sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at));

    if (!runs.length) {
      throw new Error(failures.map(item => item.reason.message).join("; ") || "No workflow results are available.");
    }
    renderRuns(runs);
    if (failures.length) {
      statusEl.textContent += ` Some workflow results could not be loaded: ${failures.map(item => item.reason.message).join("; ")}.`;
    }
  } catch (error) {
    statusEl.textContent = `Could not load live results: ${error.message} Use the direct workflow links above.`;
  } finally {
    refreshButton.disabled = false;
    refreshButton.textContent = "Refresh results";
  }
}

refreshButton.addEventListener("click", refresh);
refresh();
