const $ = (id) => document.getElementById(id);
let currentQuestion = null;
let selectedHistoryId = null;

async function ask(question) {
  $("loading").classList.remove("hidden");
  $("answer-block").classList.add("hidden");
  $("error").classList.add("hidden");

  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const detail = err?.detail;
      const msg = (detail && typeof detail === "object" && "message" in detail)
        ? detail.message
        : `HTTP ${res.status}`;
      throw new Error(msg);
    }
    const data = await res.json();
    renderAnswer(data);
    currentQuestion = data.question ?? question;
    selectedHistoryId = data.history_id;
    await loadHistory();
  } catch (e) {
    $("error").textContent = `Ошибка: ${e.message}`;
    $("error").classList.remove("hidden");
  } finally {
    $("loading").classList.add("hidden");
  }
}

function renderAnswer(data) {
  $("answer").textContent = data.answer;
  const ol = $("sources");
  ol.innerHTML = "";
  for (const s of data.sources) {
    const li = document.createElement("li");
    const page = s.page_start ? `, стр. ${s.page_start}` : "";
    const title = s.title ? `, «${s.title}»` : "";
    const score = s.score != null ? ` (score: ${s.score.toFixed(3)})` : "";
    li.innerHTML = `<strong>[${s.source}${page}${title}]</strong>${score}<br><span class="snippet"></span>`;
    li.querySelector(".snippet").textContent = s.snippet;
    ol.appendChild(li);
  }
  $("answer-block").classList.remove("hidden");
}

async function loadHistory() {
  const search = $("search").value.trim();
  const url = new URL("/api/history", window.location.origin);
  url.searchParams.set("limit", "30");
  if (search) url.searchParams.set("search", search);

  const res = await fetch(url);
  const data = await res.json();
  const ul = $("history-list");
  ul.innerHTML = "";
  for (const item of data.items) {
    const li = document.createElement("li");
    li.textContent = item.question_preview;
    li.title = item.timestamp;
    li.dataset.id = String(item.id);
    if (item.status === "no_info") li.classList.add("no-info");
    if (item.id === selectedHistoryId) li.classList.add("selected");
    li.onclick = () => openHistory(item.id);
    ul.appendChild(li);
  }
}

async function openHistory(id) {
  const res = await fetch(`/api/history/${id}`);
  if (!res.ok) return;
  const data = await res.json();

  currentQuestion = data.question ?? null;
  selectedHistoryId = id;

  document.querySelectorAll("#history-list li.selected")
    .forEach(el => el.classList.remove("selected"));
  const li = document.querySelector(`#history-list li[data-id="${id}"]`);
  if (li) li.classList.add("selected");

  renderAnswer(data);
}

$("ask-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const q = $("question").value.trim();
  if (q) ask(q);
});

$("search").addEventListener("input", () => loadHistory());

$("clear-history").addEventListener("click", async () => {
  if (!confirm("Удалить всю историю?")) return;
  await fetch("/api/history", { method: "DELETE" });

  selectedHistoryId = null;
  currentQuestion = null;
  $("answer-block").classList.add("hidden");
  $("error").classList.add("hidden");

  await loadHistory();
});

$("reask-btn").addEventListener("click", async () => {
  if (!currentQuestion) return;
  const btn = $("reask-btn");
  btn.disabled = true;
  try {
    await ask(currentQuestion);
  } finally {
    btn.disabled = false;
  }
});

loadHistory();