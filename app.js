const DATA_URL = "data/episode-01-v1.2.json";

const state = {
  data: null,
  scenes: [],
  sceneIndex: 0,
  speaker: "all",
  view: "reader"
};

const els = {};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  cacheElements();
  bindStaticEvents();

  try {
    const res = await fetch(DATA_URL, { cache: "no-store" });
    if (!res.ok) throw new Error(`Failed to load episode data: ${res.status}`);
    state.data = await res.json();
    state.scenes = flattenScenes(state.data.acts);

    fillAudit();
    buildSceneNav();
    buildSpeakerFilter();

    const hashLine = location.hash.match(/^#L\d{3}$/i)?.[0]?.slice(1).toUpperCase();
    const hashScene = location.hash.match(/^#scene-(\d{2})$/i)?.[0]?.slice(1).toLowerCase();

    if (hashLine) {
      const idx = state.scenes.findIndex(scene => scene.lines.some(line => line.id === hashLine));
      if (idx >= 0) state.sceneIndex = idx;
    } else if (hashScene) {
      const idx = state.scenes.findIndex(scene => scene.id === hashScene);
      if (idx >= 0) state.sceneIndex = idx;
    } else {
      const saved = Number(localStorage.getItem("midnight-bet-scene-index"));
      if (Number.isInteger(saved) && saved >= 0 && saved < state.scenes.length) state.sceneIndex = saved;
    }

    renderScene();

    if (hashLine) requestAnimationFrame(() => scrollToLine(hashLine, false));
  } catch (error) {
    els.storyLines.innerHTML = `<div class="load-error"><strong>Reader data could not load.</strong><br>${escapeHtml(error.message)}</div>`;
  }
}

function cacheElements() {
  [
    "scene-nav", "story-lines", "current-act", "current-scene", "scene-range",
    "prev-scene", "next-scene", "speaker-filter", "total-lines",
    "dialogue-count", "unknown-count", "scene-menu", "sidebar-close"
  ].forEach(id => {
    const camel = id.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    els[camel] = document.getElementById(id);
  });
  els.sidebar = document.querySelector(".scene-sidebar");
  els.navBtns = [...document.querySelectorAll(".nav-btn")];
  els.views = [...document.querySelectorAll(".view")];
}

function bindStaticEvents() {
  els.navBtns.forEach(btn => btn.addEventListener("click", () => switchView(btn.dataset.view)));
  els.prevScene.addEventListener("click", () => stepScene(-1));
  els.nextScene.addEventListener("click", () => stepScene(1));
  els.speakerFilter.addEventListener("change", e => {
    state.speaker = e.target.value;
    renderScene();
  });
  els.sceneMenu.addEventListener("click", () => els.sidebar.classList.add("open"));
  els.sidebarClose.addEventListener("click", () => els.sidebar.classList.remove("open"));

  window.addEventListener("hashchange", () => {
    const id = location.hash.slice(1).toUpperCase();
    if (/^L\d{3}$/.test(id)) {
      const idx = state.scenes.findIndex(scene => scene.lines.some(line => line.id === id));
      if (idx >= 0 && idx !== state.sceneIndex) {
        state.sceneIndex = idx;
        renderScene();
      }
      requestAnimationFrame(() => scrollToLine(id, true));
    }
  });
}

function switchView(view) {
  state.view = view;
  els.navBtns.forEach(btn => btn.classList.toggle("active", btn.dataset.view === view));
  els.views.forEach(section => section.classList.toggle("active", section.id === `${view}-view`));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function flattenScenes(acts) {
  const scenes = [];
  acts.forEach(act => {
    act.scenes.forEach(scene => {
      const numbered = scene.lines.filter(line => line.n);
      scenes.push({
        ...scene,
        actId: act.id,
        actTitle: act.title,
        firstLine: numbered[0]?.id || "",
        lastLine: numbered[numbered.length - 1]?.id || ""
      });
    });
  });
  return scenes;
}

function fillAudit() {
  els.totalLines.textContent = state.data.totals.lines;
  els.dialogueCount.textContent = state.data.totals.dialogueBlocks;
  els.unknownCount.textContent = state.data.totals.unknownSpeakers;
}

function buildSceneNav() {
  els.sceneNav.innerHTML = "";
  state.data.acts.forEach(act => {
    const group = document.createElement("section");
    group.className = "act-group";

    const title = document.createElement("div");
    title.className = "act-title";
    title.textContent = act.title;
    group.appendChild(title);

    act.scenes.forEach(scene => {
      const idx = state.scenes.findIndex(s => s.id === scene.id);
      const flat = state.scenes[idx];
      const btn = document.createElement("button");
      btn.className = "scene-nav-btn";
      btn.dataset.sceneIndex = idx;
      btn.innerHTML = `<span class="scene-label">${escapeHtml(scene.title.replace(/^Scene \d+ — /, ""))}</span><span class="scene-lines">${flat.firstLine}–${flat.lastLine}</span>`;
      btn.addEventListener("click", () => {
        state.sceneIndex = idx;
        state.speaker = "all";
        els.speakerFilter.value = "all";
        renderScene();
        els.sidebar.classList.remove("open");
        history.replaceState(null, "", `#${flat.id}`);
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
      group.appendChild(btn);
    });

    els.sceneNav.appendChild(group);
  });
}

function buildSpeakerFilter() {
  const speakers = new Set();
  state.scenes.forEach(scene => scene.lines.forEach(line => {
    if (line.speaker) speakers.add(line.speaker);
  }));
  [...speakers].sort().forEach(name => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    els.speakerFilter.appendChild(option);
  });
}

function renderScene() {
  if (!state.scenes.length) return;
  const scene = state.scenes[state.sceneIndex];

  localStorage.setItem("midnight-bet-scene-index", String(state.sceneIndex));

  els.currentAct.textContent = scene.actTitle;
  els.currentScene.textContent = scene.title;
  els.sceneRange.textContent = `${scene.firstLine}–${scene.lastLine} · stable source-block numbering`;

  [...document.querySelectorAll(".scene-nav-btn")].forEach(btn => {
    btn.classList.toggle("active", Number(btn.dataset.sceneIndex) === state.sceneIndex);
  });

  els.prevScene.disabled = state.sceneIndex === 0;
  els.nextScene.disabled = state.sceneIndex === state.scenes.length - 1;

  const filtered = scene.lines.filter(line => {
    if (line.kind === "break") return state.speaker === "all";
    if (state.speaker === "all") return true;
    return line.speaker === state.speaker;
  });

  els.storyLines.innerHTML = filtered.map(renderLine).join("") ||
    `<div class="empty-filter">No ${escapeHtml(state.speaker)} dialogue in this scene.</div>`;
}

function renderLine(line) {
  if (line.kind === "break") {
    return '<div class="scene-break" aria-hidden="true"><span></span><b>◆</b><span></span></div>';
  }

  const speakerMeta = line.kind === "dialogue"
    ? `<span class="speaker-chip">${escapeHtml(line.speaker)}</span><span class="line-kind">Dialogue + action</span>`
    : '<span class="narrator-chip">Narrator / thought</span><span class="line-kind">Narration / inner reaction</span>';

  return `
    <article class="story-line ${line.kind}" id="${line.id}">
      <a class="line-number" href="#${line.id}" aria-label="Link to ${line.id}">${line.id}</a>
      <div class="line-body">
        <div class="line-meta">${speakerMeta}</div>
        <p>${highlightQuotes(line.text)}</p>
      </div>
    </article>`;
}

function highlightQuotes(text) {
  const safe = escapeHtml(text);
  return safe.replace(/“([^”]+)”/g, '<span class="spoken">“$1”</span>');
}

function stepScene(delta) {
  const next = state.sceneIndex + delta;
  if (next < 0 || next >= state.scenes.length) return;
  state.sceneIndex = next;
  state.speaker = "all";
  els.speakerFilter.value = "all";
  renderScene();
  const scene = state.scenes[state.sceneIndex];
  history.replaceState(null, "", `#${scene.id}`);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function scrollToLine(id, smooth) {
  const node = document.getElementById(id);
  if (!node) return;
  node.classList.add("flash");
  node.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "center" });
  setTimeout(() => node.classList.remove("flash"), 1800);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
