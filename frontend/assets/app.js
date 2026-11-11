const els = {
  form: document.querySelector("#tool-form"),
  gallery: document.querySelector("#gallery-path"),
  targetDate: document.querySelector("#target-date"),
  recursive: document.querySelector("#recursive"),
  folder: document.querySelector("#folder-name"),
  images: document.querySelector("#image-paths"),
  destination: document.querySelector("#destination-folder"),
  traceState: document.querySelector("#trace-state"),
  traceEmpty: document.querySelector("#trace-empty"),
  traceContent: document.querySelector("#trace-content"),
  timeline: document.querySelector("#timeline"),
  resultSummary: document.querySelector("#result-summary"),
  resultJson: document.querySelector("#result-json"),
  runnerStatus: document.querySelector("#runner-status"),
  toast: document.querySelector("#toast"),
  paperCount: document.querySelector("#paper-count"),
  evidenceCount: document.querySelector("#evidence-count"),
  evidenceList: document.querySelector("#evidence-list"),
  researchResults: document.querySelector("#research-results"),
  sectionContent: document.querySelector("#section-content"),
  sectionTitle: document.querySelector("#section-title"),
  gateCard: document.querySelector("#gate-card"),
  gateMetric: document.querySelector("#gate-metric"),
  buildState: document.querySelector("#build-state"),
  aiStatus: document.querySelector("#ai-status"),
  loginScreen: document.querySelector("#login-screen"),
  candidateCount: document.querySelector("#candidate-count"),
  candidateList: document.querySelector("#candidate-list"),
  runList: document.querySelector("#run-list"),
};

let workspaceState = null;
let searchResults = [];
let activeSection = "literature_review";

function escapeHTML(value = "") {
  return String(value).replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[character]);
}

async function api(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; }
  catch { data = { detail: text || `Server returned ${response.status}` }; }
  if (response.status === 401) els.loginScreen.classList.remove("hidden");
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}

const toolLabels = {
  retrieve_images_by_date: "Find images",
  create_folder: "Create folder",
  copy_images: "Copy images",
};

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("show");
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => els.toast.classList.remove("show"), 3200);
}

function setTraceState(label, style) {
  els.traceState.textContent = label;
  els.traceState.className = `trace-state ${style}`;
}

function selectedTool() {
  return document.querySelector('input[name="tool"]:checked').value;
}

function toolArguments(tool) {
  if (tool === "retrieve_images_by_date") {
    return { target_date: els.targetDate.value, recursive: els.recursive.checked };
  }
  if (tool === "create_folder") return { folder: els.folder.value.trim() };
  return {
    images: els.images.value.split("\n").map((value) => value.trim()).filter(Boolean),
    destination_folder: els.destination.value.trim(),
  };
}

function showResult(result, elapsed, tool) {
  els.traceEmpty.classList.add("hidden");
  els.traceContent.classList.remove("hidden");
  const statusText = result.success ? "Completed safely" : "Stopped safely";
  setTraceState(result.success ? "Success" : "Blocked", result.success ? "success" : "failure");
  els.timeline.innerHTML = `
    <li><strong>Request checked</strong><br />Tool is on the allowlist</li>
    <li><strong>Gallery boundary checked</strong><br />Path rules applied</li>
    <li><strong>${statusText}</strong><br />Finished in ${elapsed} ms</li>
  `;
  const detail = result.success
    ? `${toolLabels[tool]} returned a valid structured result.`
    : `${toolLabels[tool]} did not run: ${result.error || "Unknown error"}`;
  els.resultSummary.innerHTML = `<strong>${statusText}</strong><br />${detail}`;
  els.resultJson.textContent = JSON.stringify(result, null, 2);
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error("Runner unavailable");
    const health = await response.json();
    els.runnerStatus.textContent = health.status;
    els.runnerStatus.style.color = "var(--mint)";
  } catch {
    els.runnerStatus.textContent = "offline";
    els.runnerStatus.style.color = "#ff9e96";
  }
}

function paperCard(paper, index, saved = false) {
  const authors = (paper.authors || []).slice(0, 3).join(", ") || "Authors unavailable";
  const action = saved ? `<span class="saved-label">Saved evidence</span>` : `<button class="button compact ghost save-paper" data-index="${index}">Add evidence</button>`;
  return `<article class="paper-card">
    <div class="paper-meta"><span>${escapeHTML(paper.year || "n.d.")}</span><span>${escapeHTML(paper.paper_type || "paper")}</span></div>
    <h4>${escapeHTML(paper.title)}</h4>
    <p>${escapeHTML(authors)}</p>
    <div class="paper-foot"><a href="${escapeHTML(paper.url)}" target="_blank" rel="noreferrer">DOI: ${escapeHTML(paper.doi)}</a>${action}</div>
  </article>`;
}

function renderWorkspace() {
  const state = workspaceState;
  els.paperCount.textContent = String(state.paper_count).padStart(2, "0");
  els.evidenceCount.textContent = state.paper_count;
  els.evidenceList.innerHTML = state.papers.length
    ? state.papers.map((paper, index) => paperCard(paper, index, true)).join("")
    : '<div class="soft-empty">No papers saved yet.</div>';
  const approved = state.build_unlocked;
  els.gateCard.classList.toggle("locked", !approved);
  els.gateCard.classList.toggle("approved", approved);
  document.querySelector("#gate-icon").textContent = approved ? "✓" : "⌾";
  document.querySelector("#gate-title").textContent = approved ? "Development is unlocked" : "Development is locked";
  document.querySelector("#gate-description").textContent = approved
    ? "Method approved. Build execution is available."
    : "Method approval required before build execution.";
  document.querySelector("#approve-method").classList.toggle("hidden", approved);
  document.querySelector("#approval-confirm").closest("label").classList.toggle("hidden", approved);
  document.querySelector("#reopen-method").classList.toggle("hidden", !approved);
  els.gateMetric.textContent = approved ? "OPEN" : "LOCKED";
  els.buildState.textContent = approved ? "Unlocked" : "Locked";
  els.buildState.classList.toggle("open", approved);
  const runButton = els.form.querySelector('button[type="submit"]');
  runButton.disabled = !approved;
  runButton.title = approved ? "" : "Approve the methodology first";
  els.aiStatus.textContent = "Local automation active";
  const section = state.sections.find((item) => item.section_key === activeSection);
  if (section) {
    els.sectionTitle.textContent = section.title;
    els.sectionContent.value = section.content;
  }
  const candidates = state.research_candidates || [];
  els.candidateCount.textContent = candidates.length;
  els.candidateList.innerHTML = candidates.length ? candidates.map((candidate) => {
    const paper = candidate.paper;
    return `<article class="paper-card"><div class="paper-meta"><span>${escapeHTML(paper.year || "n.d.")}</span><span>Pending</span></div><h4>${escapeHTML(paper.title)}</h4><p>${escapeHTML(candidate.query)}</p><div class="paper-foot"><a href="${escapeHTML(paper.url)}" target="_blank" rel="noreferrer">${escapeHTML(paper.doi)}</a><button class="button compact ghost approve-candidate" data-doi="${escapeHTML(paper.doi)}">Approve</button></div></article>`;
  }).join("") : '<div class="soft-empty">The next operation will add papers here.</div>';
  const runs = state.job_runs || [];
  els.runList.innerHTML = runs.length ? runs.map((run) => `<div class="run-item"><strong>${escapeHTML(run.job_name)} · ${escapeHTML(run.status)}</strong><small>${escapeHTML(run.started_at)}</small></div>`).join("") : '<div class="soft-empty">No autonomous runs yet.</div>';
  document.querySelector("#operation-database").textContent = state.operation.database === "postgresql" ? "Supabase connected" : "Local SQLite";
  document.querySelector("#operation-telegram").textContent = state.operation.telegram ? "Connected" : "Not connected";
  document.querySelector("#operation-schedule").textContent = state.operation.schedule;
}

els.candidateList.addEventListener("click", async (event) => {
  const button = event.target.closest(".approve-candidate");
  if (!button) return;
  button.disabled = true;
  try {
    await api(`/api/research/candidates/${encodeURIComponent(button.dataset.doi)}/approve`, { method: "POST" });
    await loadWorkspace(); showToast("Paper approved and added to evidence.");
  } catch (error) { button.disabled = false; showToast(error.message); }
});

async function loadWorkspace() {
  try {
    workspaceState = await api("/api/workspace");
    renderWorkspace();
  } catch (error) {
    showToast(error.message);
  }
}

document.querySelector("#research-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button");
  const query = document.querySelector("#research-query").value.trim();
  button.disabled = true; button.textContent = "Searching…";
  els.researchResults.innerHTML = '<div class="soft-empty">Research Agent is checking Crossref…</div>';
  try {
    const data = await api(`/api/research/search?query=${encodeURIComponent(query)}&rows=8`);
    searchResults = data.papers;
    els.researchResults.innerHTML = searchResults.length
      ? searchResults.map((paper, index) => paperCard(paper, index)).join("")
      : '<div class="soft-empty">No matching DOI records found. Try a wider query.</div>';
  } catch (error) {
    els.researchResults.innerHTML = `<div class="soft-empty error-text">${escapeHTML(error.message)}</div>`;
  } finally {
    button.disabled = false; button.textContent = "Search papers";
  }
});

els.researchResults.addEventListener("click", async (event) => {
  const button = event.target.closest(".save-paper");
  if (!button) return;
  button.disabled = true; button.textContent = "Saving…";
  try {
    await api("/api/research/evidence", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paper: searchResults[Number(button.dataset.index)] }),
    });
    button.textContent = "Saved";
    await loadWorkspace();
    showToast("Paper added to the verified evidence library.");
  } catch (error) {
    button.disabled = false; button.textContent = "Add evidence"; showToast(error.message);
  }
});

document.querySelector("#section-tabs").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-section]");
  if (!button) return;
  activeSection = button.dataset.section;
  document.querySelectorAll("#section-tabs button").forEach((item) => item.classList.toggle("active", item === button));
  renderWorkspace();
});

async function saveSection(showMessage = true) {
  const result = await api(`/api/thesis/sections/${activeSection}`, {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content: els.sectionContent.value }),
  });
  await loadWorkspace();
  if (showMessage) showToast(`${result.section.title} saved.`);
}

document.querySelector("#save-section").addEventListener("click", async () => {
  try { await saveSection(); } catch (error) { showToast(error.message); }
});

async function draftSection() {
  const button = document.querySelector("#build-outline");
  button.disabled = true; button.textContent = "Building…";
  try {
    await saveSection(false);
    const result = await api("/api/thesis/draft", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ section_key: activeSection }),
    });
    await loadWorkspace();
    showToast("Evidence outline created locally.");
  } catch (error) { showToast(error.message); }
  finally { button.disabled = false; button.textContent = "Build evidence outline"; }
}

document.querySelector("#build-outline").addEventListener("click", draftSection);

document.querySelector("#approve-method").addEventListener("click", async () => {
  try {
    if (activeSection === "methodology") await saveSection(false);
    await api("/api/methodology/approve", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmed: document.querySelector("#approval-confirm").checked }),
    });
    await loadWorkspace(); showToast("Methodology approved. Development is unlocked.");
  } catch (error) { showToast(error.message); }
});

document.querySelector("#reopen-method").addEventListener("click", async () => {
  try { await api("/api/methodology/reopen", { method: "POST" }); await loadWorkspace(); showToast("Methodology reopened. Development is locked."); }
  catch (error) { showToast(error.message); }
});

async function loadDemo() {
  const buttons = [document.querySelector("#load-demo")].filter(Boolean);
  buttons.forEach((button) => { button.disabled = true; button.textContent = "Preparing…"; });
  try {
    const response = await fetch("/api/demo/setup", { method: "POST" });
    const demo = await response.json();
    els.gallery.value = demo.gallery;
    els.targetDate.value = demo.date;
    showToast(demo.message);
    document.querySelector("#command-lab").scrollIntoView({ behavior: "smooth" });
  } catch {
    showToast("Could not prepare the demo gallery.");
  } finally {
    buttons[0].disabled = false; buttons[0].textContent = "Use demo data";
  }
}

document.querySelectorAll('input[name="tool"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    document.querySelectorAll(".tool-tab").forEach((tab) => tab.classList.toggle("active", tab.contains(radio)));
    document.querySelectorAll("[data-tool-fields]").forEach((group) => group.classList.toggle("hidden", group.dataset.toolFields !== radio.value));
  });
});

els.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submit = els.form.querySelector('button[type="submit"]');
  const tool = selectedTool();
  submit.disabled = true;
  submit.querySelector("span:last-child").textContent = "Running…";
  setTraceState("Running", "running");
  const started = performance.now();
  try {
    const response = await fetch("/api/tools/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ gallery: els.gallery.value.trim(), tool, arguments: toolArguments(tool) }),
    });
    const result = await response.json();
    showResult(result, Math.round(performance.now() - started), tool);
  } catch (error) {
    showResult({ success: false, tool, data: {}, error: error.message }, Math.round(performance.now() - started), tool);
  } finally {
    submit.disabled = false;
    submit.querySelector("span:last-child").textContent = "Run safe tool";
  }
});

document.querySelector("#load-demo").addEventListener("click", loadDemo);
document.querySelector("#refresh-health").addEventListener("click", checkHealth);

document.querySelector("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const error = document.querySelector("#login-error");
  try {
    await api("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password: document.querySelector("#login-password").value }) });
    els.loginScreen.classList.add("hidden"); error.textContent = ""; await loadWorkspace();
  } catch (loginError) { error.textContent = loginError.message; }
});

document.querySelector("#logout-button").addEventListener("click", async () => {
  await api("/api/auth/logout", { method: "POST" });
  els.loginScreen.classList.remove("hidden");
});

async function checkAuth() {
  try {
    const status = await api("/api/auth/status");
    els.loginScreen.classList.toggle("hidden", status.authenticated);
    document.querySelector("#logout-button").classList.toggle("hidden", !status.required);
    if (status.authenticated) await loadWorkspace();
  } catch (error) { showToast(error.message); }
}

const navItems = [...document.querySelectorAll(".nav-item")];
const sections = navItems.map((item) => document.querySelector(item.getAttribute("href"))).filter(Boolean);
const observer = new IntersectionObserver((entries) => {
  const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
  if (!visible) return;
  navItems.forEach((item) => item.classList.toggle("active", item.getAttribute("href") === `#${visible.target.id}`));
}, { rootMargin: "-25% 0px -60%", threshold: [0.05, 0.3] });
sections.forEach((section) => observer.observe(section));

checkHealth();
checkAuth();
