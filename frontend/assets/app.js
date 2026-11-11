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
  officeGrid: document.querySelector("#office-grid"),
  agentChatFeed: document.querySelector("#agent-chat-feed"),
  citationFile: document.querySelector("#citation-file"),
  citationApproved: document.querySelector("#citation-approved"),
  importCitations: document.querySelector("#import-citations"),
  importResult: document.querySelector("#import-result"),
  planxOffice: document.querySelector("#planx-office"),
  planxStatus: document.querySelector("#planx-status"),
  planxBubble: document.querySelector("#planx-bubble"),
  planxCharacter: document.querySelector("#planx-character"),
  planxSourceCount: document.querySelector("#planx-source-count"),
  planxSourceList: document.querySelector("#planx-source-list"),
  studioWordCount: document.querySelector("#studio-word-count"),
  clearAllSources: document.querySelector("#clear-all-sources"),
  planxSourceSearch: document.querySelector("#planx-source-search"),
  planxSearchResults: document.querySelector("#planx-search-results"),
  operationEvidenceCount: document.querySelector("#operation-evidence-count"),
  operationEvidenceList: document.querySelector("#operation-evidence-list"),
};

let workspaceState = null;
let searchResults = [];
let activeSection = "literature_review";
let planxMode = "idle";
let planxTimer = null;
let selectedPlanxDois = new Set();
let planxSelectionLoaded = false;

const planxMessages = {
  idle: ["Coffee ready. Send me approved evidence when you are.", "I’m reviewing the structure in my head.", "Click Build evidence outline when you want me to start."],
  writing: ["I’m grouping sources by themes—not summarising them one by one."],
  filing: ["Saving this draft into the thesis workspace."],
  done: ["Draft ready. Your review is the next checkpoint."],
  error: ["I hit a problem. Check the message and we’ll try again."],
};

function setPlanxState(mode, message, returnToIdle = false) {
  if (!els.planxOffice) return;
  planxMode = mode;
  window.clearTimeout(planxTimer);
  els.planxOffice.classList.remove("state-idle", "state-writing", "state-filing", "state-done", "state-error");
  els.planxOffice.classList.add(`state-${mode}`);
  const labels = { idle: "Coffee break", writing: "Writing", filing: "Filing draft", done: "Ready for review", error: "Needs attention" };
  els.planxStatus.textContent = labels[mode];
  els.planxBubble.textContent = message || planxMessages[mode][0];
  if (els.aiStatus) els.aiStatus.textContent = `${labels[mode]} · click Planx to talk`;
  if (returnToIdle) planxTimer = window.setTimeout(() => setPlanxState("idle"), 5200);
}

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
  const sourceTag = paper.source === "Approved Introduction" ? "INTRO APPROVED" : (paper.paper_type || "paper");
  return `<article class="paper-card">
    <div class="paper-meta"><span>${escapeHTML(paper.year || "n.d.")}</span><span>${escapeHTML(sourceTag)}</span></div>
    <h4>${escapeHTML(paper.title)}</h4>
    <p>${escapeHTML(authors)}</p>
    <div class="paper-foot"><a href="${escapeHTML(paper.url)}" target="_blank" rel="noreferrer">DOI: ${escapeHTML(paper.doi)}</a>${action}</div>
  </article>`;
}

function renderPlanxSources(papers) {
  if (!els.planxSourceList) return;
  if (!planxSelectionLoaded) {
    const stored = window.localStorage.getItem("xeng-planx-sources");
    try { selectedPlanxDois = new Set(stored === null ? [] : JSON.parse(stored)); }
    catch { selectedPlanxDois = new Set(); }
    planxSelectionLoaded = true;
  }
  const available = new Set(papers.map((paper) => paper.doi));
  selectedPlanxDois = new Set([...selectedPlanxDois].filter((doi) => available.has(doi)));
  els.planxSourceCount.textContent = `${selectedPlanxDois.size} selected`;
  const selected = papers.filter((paper) => selectedPlanxDois.has(paper.doi));
  els.planxSourceList.innerHTML = selected.length ? selected.map((paper) => {
    const lead = (paper.authors || ["Unknown"])[0].split(" ").slice(-1)[0];
    const citation = `${lead}${(paper.authors || []).length > 1 ? " et al." : ""}, ${paper.year || "n.d."}`;
    return `<article class="planx-selected-source"><div><strong>${escapeHTML(paper.title)}</strong><small>${escapeHTML(citation)}</small></div><button type="button" class="remove-planx-source" data-doi="${escapeHTML(paper.doi)}" aria-label="Remove ${escapeHTML(paper.title)}">×</button></article>`;
  }).join("") : '<div class="soft-empty">No papers selected. Search above to add evidence.</div>';
  renderPlanxSearchResults(papers);
}

function renderPlanxSearchResults(papers = workspaceState?.papers || []) {
  const query = (els.planxSourceSearch?.value || "").trim().toLowerCase();
  if (!query) return els.planxSearchResults.classList.add("hidden");
  const matches = papers.filter((paper) => {
    const haystack = [paper.title, ...(paper.authors || []), paper.year].join(" ").toLowerCase();
    return haystack.includes(query);
  }).slice(0, 5);
  els.planxSearchResults.innerHTML = matches.length ? matches.map((paper) => {
    const added = selectedPlanxDois.has(paper.doi);
    return `<button type="button" class="planx-search-result" data-doi="${escapeHTML(paper.doi)}" ${added ? "disabled" : ""}><span><strong>${escapeHTML(paper.title)}</strong><small>${escapeHTML((paper.authors || []).slice(0, 2).join(", "))} · ${escapeHTML(paper.year || "n.d.")}</small></span><b>${added ? "Added" : "+ Add"}</b></button>`;
  }).join("") : '<div class="planx-no-result">No approved papers match that search.</div>';
  els.planxSearchResults.classList.remove("hidden");
}

function renderOperationEvidence(papers) {
  if (!els.operationEvidenceList) return;
  els.operationEvidenceCount.textContent = papers.length;
  els.operationEvidenceList.innerHTML = papers.length ? papers.map((paper) => `<article><div><strong>${escapeHTML(paper.title)}</strong><small>${escapeHTML((paper.authors || ["Unknown"])[0])} · ${escapeHTML(paper.year || "n.d.")}</small></div><span>${paper.abstract ? "Claim-ready" : "Citation approved"}</span></article>`).join("") : '<div class="soft-empty">No approved papers yet.</div>';
}

function savePlanxSelection(rerender = true) {
  window.localStorage.setItem("xeng-planx-sources", JSON.stringify([...selectedPlanxDois]));
  if (rerender) renderPlanxSources(workspaceState?.papers || []);
  else els.planxSourceCount.textContent = `${selectedPlanxDois.size} selected`;
}

function updateWordCount() {
  if (!els.studioWordCount) return;
  const words = els.sectionContent.value.trim().split(/\s+/).filter(Boolean).length;
  els.studioWordCount.textContent = `${words} word${words === 1 ? "" : "s"}`;
}

if (els.citationFile) {
  els.citationFile.addEventListener("change", () => {
    const file = els.citationFile.files[0];
    document.querySelector("#citation-file-label").textContent = file ? file.name : "Choose .txt or .md";
  });
}

if (els.importCitations) {
  els.importCitations.addEventListener("click", async () => {
    const file = els.citationFile.files[0];
    if (!file) return showToast("Choose your citations .txt or .md file first.");
    if (!els.citationApproved.checked) return showToast("Confirm the Introduction approval status first.");
    if (file.size > 100000) return showToast("The bibliography file must be smaller than 100 KB.");
    els.importCitations.disabled = true;
    els.importCitations.textContent = "Evi-Revy is checking…";
    try {
      const result = await api("/api/research/import-citations", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: await file.text(), approved_for_introduction: true }),
      });
      els.importResult.classList.remove("hidden");
      els.importResult.innerHTML = `<strong>${result.imported} approved sources imported</strong><span>${result.duplicates} duplicate(s) removed · ${result.issues.length} correction note(s)</span>`;
      await loadWorkspace();
      showToast("Approved sources are now available to Planx.");
    } catch (error) {
      showToast(error.message);
    } finally {
      els.importCitations.disabled = false;
      els.importCitations.textContent = "Import to XENG";
    }
  });
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
  if (planxMode === "idle" && els.aiStatus) els.aiStatus.textContent = "Coffee break · click Planx to talk";
  const section = state.sections.find((item) => item.section_key === activeSection);
  if (section) {
    els.sectionTitle.textContent = section.title;
    els.sectionContent.value = section.content;
    updateWordCount();
  }
  renderPlanxSources(state.papers || []);
  renderOperationEvidence(state.papers || []);
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
  renderAgentOffice(state.agents || [], state.agent_messages || []);
}

const agentColours = {
  "scoot": "mint", "evi-revy": "pink", "planx": "blue",
  "xengineer": "orange", "teehee": "purple", "cordy": "yellow",
};

function renderAgentOffice(agents, messages) {
  if (!els.officeGrid) return;
  els.officeGrid.innerHTML = agents.map((agent, index) => `
    <article class="pixel-desk status-${escapeHTML(agent.status)}" style="--delay:${index * -.37}s">
      <div class="speech-bubble">${escapeHTML(agent.last_message)}</div>
      <div class="desk-scene">
        <div class="pixel-person ${agentColours[agent.agent_key] || "mint"}">
          <i class="pixel-hair"></i><i class="pixel-head"></i><i class="pixel-body"></i><i class="pixel-feet"></i>
        </div>
        <div class="pixel-desk-table"><i class="pixel-monitor"></i><i class="pixel-keyboard"></i></div>
      </div>
      <div class="agent-desk-meta">
        <div><strong>${escapeHTML(agent.name)}</strong><small>${escapeHTML(agent.role)}</small></div>
        <span class="agent-status"><i></i>${escapeHTML(agent.status)}</span>
      </div>
      <p>${escapeHTML(agent.current_task)}</p>
    </article>`).join("");

  const names = Object.fromEntries(agents.map((agent) => [agent.agent_key, agent.name]));
  els.agentChatFeed.innerHTML = messages.length ? messages.slice(0, 10).map((message) => `
    <div class="chat-line"><span class="chat-avatar">${escapeHTML((names[message.sender_key] || "X").slice(0, 1))}</span>
      <div><strong>${escapeHTML(names[message.sender_key] || message.sender_key)} <em>→ ${escapeHTML(names[message.receiver_key] || message.receiver_key)}</em></strong>
      <p>${escapeHTML(message.message)}</p></div><time>${escapeHTML(new Date(message.created_at).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"}))}</time></div>`).join("")
    : '<div class="soft-empty">No handoffs yet. The next cloud cycle will start the conversation.</div>';
}

function updateOfficeClock() {
  const clock = document.querySelector("#office-clock");
  if (clock) clock.textContent = new Date().toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"});
}
updateOfficeClock();
window.setInterval(updateOfficeClock, 30000);

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
  const labels = { literature_review: "literature review", methodology: "methodology", expected_results: "expected results" };
  setPlanxState("idle", `Opened ${labels[activeSection]}. I’m ready when you are.`);
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
  setPlanxState("filing");
  try {
    await saveSection();
    setPlanxState("done", "Draft saved safely. I’ll keep it ready for your next instruction.", true);
  } catch (error) {
    setPlanxState("error", error.message, true); showToast(error.message);
  }
});

async function draftSection() {
  const button = document.querySelector("#build-outline");
  button.disabled = true; button.textContent = "Building…";
  if (!selectedPlanxDois.size) {
    button.disabled = false; button.textContent = "Ask Planx to write";
    setPlanxState("error", "Choose at least one source from my evidence shelf first.", true);
    return showToast("Select at least one source for Planx.");
  }
  setPlanxState("writing");
  try {
    await saveSection(false);
    const result = await api("/api/thesis/draft", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ section_key: activeSection, evidence_dois: [...selectedPlanxDois] }),
    });
    await loadWorkspace();
    setPlanxState("done", "Academic draft ready. Please review the wording and citations before saving it.", true);
    showToast("Planx prepared an evidence-linked academic draft.");
  } catch (error) { setPlanxState("error", error.message, true); showToast(error.message); }
  finally { button.disabled = false; button.textContent = "Ask Planx to write"; }
}

document.querySelector("#build-outline").addEventListener("click", draftSection);

if (els.planxCharacter) {
  let planxHello = 0;
  els.planxCharacter.addEventListener("click", () => {
    if (["writing", "filing"].includes(planxMode)) return;
    const messages = planxMessages.idle;
    setPlanxState("done", messages[planxHello++ % messages.length], true);
  });
}

els.sectionContent.addEventListener("input", updateWordCount);

els.planxSourceSearch.addEventListener("input", () => renderPlanxSearchResults());

els.planxSearchResults.addEventListener("click", (event) => {
  const button = event.target.closest(".planx-search-result");
  if (!button || button.disabled) return;
  selectedPlanxDois.add(button.dataset.doi);
  savePlanxSelection();
  els.planxSourceSearch.value = "";
  els.planxSearchResults.classList.add("hidden");
  setPlanxState("idle", `${selectedPlanxDois.size} source${selectedPlanxDois.size === 1 ? "" : "s"} selected for my next draft.`);
});

els.planxSourceList.addEventListener("click", (event) => {
  const button = event.target.closest(".remove-planx-source");
  if (!button) return;
  selectedPlanxDois.delete(button.dataset.doi);
  savePlanxSelection();
  setPlanxState("idle", `${selectedPlanxDois.size} source${selectedPlanxDois.size === 1 ? "" : "s"} selected for my next draft.`);
});

els.clearAllSources.addEventListener("click", () => {
  selectedPlanxDois.clear();
  savePlanxSelection();
  setPlanxState("idle", "Evidence shelf cleared. Choose only the papers you want me to use.");
});

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
