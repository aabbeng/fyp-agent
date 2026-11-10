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
};

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

async function loadDemo() {
  const buttons = [document.querySelector("#load-demo"), document.querySelector("#load-demo-top")];
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
    buttons[1].disabled = false; buttons[1].textContent = "Load demo gallery";
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
document.querySelector("#load-demo-top").addEventListener("click", loadDemo);
document.querySelector("#refresh-health").addEventListener("click", checkHealth);

const navItems = [...document.querySelectorAll(".nav-item")];
const sections = navItems.map((item) => document.querySelector(item.getAttribute("href"))).filter(Boolean);
const observer = new IntersectionObserver((entries) => {
  const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
  if (!visible) return;
  navItems.forEach((item) => item.classList.toggle("active", item.getAttribute("href") === `#${visible.target.id}`));
}, { rootMargin: "-25% 0px -60%", threshold: [0.05, 0.3] });
sections.forEach((section) => observer.observe(section));

checkHealth();
