const EPISODES = {
  1: { url: "data/episode-01-v1.3.json", label: "Episode 01" },
  2: { url: "data/episode-02-v1.3.json", label: "Episode 02" }
};

const STORY_HIGHLIGHTS = [
  { phrase: "upper chest", category: "visibility" },
  { phrase: "upper curve", category: "visibility" },
  { phrase: "open neckline", category: "visibility" },
  { phrase: "neckline", category: "visibility" },
  { phrase: "bare shoulder", category: "visibility" },
  { phrase: "bare shoulders", category: "visibility" },
  { phrase: "bare arms", category: "visibility" },
  { phrase: "sleeveless", category: "visibility" },
  { phrase: "pallu slid from her shoulder", category: "visibility" },
  { phrase: "pallu", category: "visibility" },
  { phrase: "shawl", category: "visibility" },
  { phrase: "shrug", category: "visibility" },
  { phrase: "waist exposed", category: "visibility" },
  { phrase: "waist", category: "visibility" },
  { phrase: "visible", category: "visibility" },
  { phrase: "exposed", category: "visibility" },
  { phrase: "uncovered line", category: "visibility" },
  { phrase: "more open", category: "visibility" },
  { phrase: "without the shawl", category: "visibility" },
  { phrase: "without the shrug", category: "visibility" },
  { phrase: "blouse line", category: "visibility" },

  { phrase: "eyes dropped", category: "gaze" },
  { phrase: "eyes moved", category: "gaze" },
  { phrase: "eyes shifted", category: "gaze" },
  { phrase: "trying not to look again", category: "gaze" },
  { phrase: "looked again", category: "gaze" },
  { phrase: "watching", category: "gaze" },
  { phrase: "noticed", category: "gaze" },
  { phrase: "register that she looked different", category: "gaze" },
  { phrase: "caught the movement", category: "gaze" },

  { phrase: "deliberately", category: "choice" },
  { phrase: "she had chosen", category: "choice" },
  { phrase: "she chose", category: "choice" },
  { phrase: "chosen the clothes", category: "choice" },
  { phrase: "chosen the place", category: "choice" },
  { phrase: "could have", category: "choice" },
  { phrase: "did not cover", category: "choice" },
  { phrase: "did not straighten immediately", category: "choice" },
  { phrase: "held the position", category: "choice" },
  { phrase: "one extra beat", category: "choice" },
  { phrase: "another beat", category: "choice" },
  { phrase: "several more seconds", category: "choice" },
  { phrase: "several seconds", category: "choice" },
  { phrase: "left the shawl", category: "choice" },
  { phrase: "slipped the overshirt", category: "choice" },
  { phrase: "put the overshirt back on", category: "choice" },
  { phrase: "restored the pallu", category: "choice" },
  { phrase: "pulled the shawl back", category: "choice" },
  { phrase: "stayed where she was", category: "choice" },

  { phrase: "he knew she had seen", category: "awareness" },
  { phrase: "she knew he knew", category: "awareness" },
  { phrase: "mutual awareness", category: "awareness" },
  { phrase: "both recognized", category: "awareness" },
  { phrase: "met her eyes", category: "awareness" },
  { phrase: "eye contact", category: "awareness" },
  { phrase: "understood the entire triangle", category: "awareness" },
  { phrase: "pulse", category: "awareness" },
  { phrase: "rush", category: "awareness" },
  { phrase: "breathing", category: "awareness" },
  { phrase: "tightened", category: "awareness" },
  { phrase: "felt exposed", category: "awareness" },
  { phrase: "face warmed", category: "awareness" },
  { phrase: "replayed", category: "awareness" },
  { phrase: "replay", category: "awareness" },

  { phrase: "joined fingers", category: "couple" },
  { phrase: "forehead briefly against his shoulder", category: "couple" },
  { phrase: "held her hand", category: "couple" },
  { phrase: "placed his hand over it", category: "couple" },
  { phrase: "touched rhea’s wrist", category: "couple" },
  { phrase: "caught the front of his shirt", category: "couple" }
].sort((a, b) => b.phrase.length - a.phrase.length);

const HIGHLIGHT_LABELS = {
  visibility: "Body / visibility",
  gaze: "Gaze / reaction",
  choice: "Deliberate choice",
  awareness: "Awareness / aftermath",
  couple: "Couple intimacy"
};

const HIGHLIGHT_MAP = new Map(STORY_HIGHLIGHTS.map(item => [item.phrase.toLowerCase(), item.category]));
const HIGHLIGHT_RE = new RegExp(
  STORY_HIGHLIGHTS.map(item => item.phrase.replace(/[.*+?^\${}()|[\]\\]/g, "\\const state = {")).join("|"),
  "gi"
);

const state = {
  data: null,
  scenes: [],
  sceneIndex: 0,
  speaker: "all",
  view: "reader",
  episode: 1
};

const els = {};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  cacheElements();
  bindStaticEvents();

  const params = new URLSearchParams(location.search);
  const requested = Number(params.get("episode"));
  const saved = Number(localStorage.getItem("midnight-bet-episode"));
  const episode = EPISODES[requested] ? requested : (EPISODES[saved] ? saved : 1);

  await loadEpisode(episode, false);
}

function cacheElements() {
  [
    "scene-nav", "story-lines", "current-act", "current-scene", "scene-range",
    "prev-scene", "next-scene", "speaker-filter", "total-lines",
    "dialogue-count", "unknown-count", "scene-menu", "sidebar-close",
    "episode-kicker", "episode-heading", "hero-copy", "prologue"
  ].forEach(id => {
    const camel = id.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    els[camel] = document.getElementById(id);
  });

  els.sidebar = document.querySelector(".scene-sidebar");
  els.navBtns = [...document.querySelectorAll(".nav-btn")];
  els.views = [...document.querySelectorAll(".view")];
}

function bindStaticEvents() {
  els.navBtns.forEach(btn => {
    if (btn.dataset.episode) {
      btn.addEventListener("click", async () => {
        switchView("reader");
        await loadEpisode(Number(btn.dataset.episode), true);
      });
    } else if (btn.dataset.view) {
      btn.addEventListener("click", () => switchView(btn.dataset.view));
    }
  });

  els.prevScene.addEventListener("click", () => stepScene(-1));
  els.nextScene.addEventListener("click", () => stepScene(1));

  els.speakerFilter.addEventListener("change", e => {
    state.speaker = e.target.value;
    renderScene();
  });

  els.sceneMenu.addEventListener("click", () => els.sidebar.classList.add("open"));
  els.sidebarClose.addEventListener("click", () => els.sidebar.classList.remove("open"));

  window.addEventListener("hashchange", handleHashChange);
}

async function loadEpisode(episode, updateUrl = true) {
  if (!EPISODES[episode]) return;

  state.episode = episode;
  state.speaker = "all";
  state.sceneIndex = 0;
  localStorage.setItem("midnight-bet-episode", String(episode));

  els.storyLines.innerHTML = '<div class="load-error">Loading episode…</div>';

  try {
    const res = await fetch(EPISODES[episode].url, { cache: "no-store" });
    if (!res.ok) throw new Error(`Failed to load episode data: ${res.status}`);

    state.data = await res.json();
    state.scenes = flattenScenes(state.data.acts);

    const savedScene = Number(localStorage.getItem(`midnight-bet-scene-index-${episode}`));
    if (Number.isInteger(savedScene) && savedScene >= 0 && savedScene < state.scenes.length) {
      state.sceneIndex = savedScene;
    }

    applyHashSelection();
    updateEpisodeChrome();
    fillAudit();
    buildSceneNav();
    buildSpeakerFilter();
    renderScene();
    setNavActive();

    if (updateUrl) {
      const url = new URL(location.href);
      url.searchParams.set("episode", String(episode));
      url.hash = "";
      history.replaceState(null, "", url);
    }

    requestAnimationFrame(() => {
      const parsed = parseLineHash();
      if (parsed && parsed.episode === episode) scrollToLine(parsed.id, false);
    });
  } catch (error) {
    els.storyLines.innerHTML = `<div class="load-error"><strong>Reader data could not load.</strong><br>${escapeHtml(error.message)}</div>`;
  }
}

function updateEpisodeChrome() {
  const ep = String(state.episode).padStart(2, "0");
  els.episodeKicker.textContent = `EPISODE ${ep} · ${state.data.version} · ${state.data.status}`;
  els.episodeHeading.textContent = state.data.episodeTitle;
  els.heroCopy.textContent = state.episode === 1
    ? "Line-numbered reader view with explicit speaker ownership. Dialogue is labeled by speaker; narration and internal reaction are visually separated."
    : "Continues directly from Episode 01. External non-graphic escalation and couple intimacy are tracked separately; speaker ownership and source-block line numbers remain explicit.";
  els.prologue.hidden = state.episode !== 1;
  document.title = `Midnight Bet — Episode ${ep} — ${state.data.episodeTitle}`;
}

function setNavActive() {
  els.navBtns.forEach(btn => {
    if (state.view === "cast") {
      btn.classList.toggle("active", btn.dataset.view === "cast");
    } else {
      btn.classList.toggle("active", Number(btn.dataset.episode) === state.episode);
    }
  });
}

function switchView(view) {
  state.view = view;
  els.views.forEach(section => section.classList.toggle("active", section.id === `${view}-view`));
  setNavActive();
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
        history.replaceState(null, "", sceneUrl(flat.id));
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
      group.appendChild(btn);
    });

    els.sceneNav.appendChild(group);
  });
}

function buildSpeakerFilter() {
  els.speakerFilter.innerHTML = '<option value="all">All lines</option>';
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

  els.speakerFilter.value = "all";
}

function renderScene() {
  if (!state.scenes.length) return;

  const scene = state.scenes[state.sceneIndex];
  localStorage.setItem(`midnight-bet-scene-index-${state.episode}`, String(state.sceneIndex));

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

  const categories = getHighlightCategories(line.text);
  const externalCategories = categories.filter(category => category !== "couple");
  const isKeyEscalation = externalCategories.length >= 2 ||
    (externalCategories.includes("choice") && (externalCategories.includes("visibility") || externalCategories.includes("gaze")));
  const isCoupleBeat = categories.includes("couple") && externalCategories.length === 0;

  const beatBadge = isKeyEscalation
    ? `<span class="beat-badge escalation-badge">KEY ESCALATION · ${externalCategories.map(c => HIGHLIGHT_LABELS[c]).join(" + ")}</span>`
    : isCoupleBeat
      ? '<span class="beat-badge couple-badge">COUPLE INTIMACY · SEPARATE TRACK</span>'
      : "";

  const beatClass = isKeyEscalation ? " key-escalation-line" : (isCoupleBeat ? " couple-intimacy-line" : "");
  const domId = `E${state.episode}-${line.id}`;

  return `
    <article class="story-line ${line.kind}${beatClass}" id="${domId}">
      <a class="line-number" href="#${domId}" aria-label="Link to Episode ${state.episode} ${line.id}">${line.id}</a>
      <div class="line-body">
        <div class="line-meta">${speakerMeta}${beatBadge}</div>
        <p>${highlightStoryText(line.text)}</p>
      </div>
    </article>`;
}

function getHighlightCategories(text) {
  const lower = text.toLowerCase();
  return [...new Set(
    STORY_HIGHLIGHTS
      .filter(item => lower.includes(item.phrase.toLowerCase()))
      .map(item => item.category)
  )];
}

function markImportantPhrases(text) {
  HIGHLIGHT_RE.lastIndex = 0;
  let html = "";
  let lastIndex = 0;
  let match;

  while ((match = HIGHLIGHT_RE.exec(text)) !== null) {
    html += escapeHtml(text.slice(lastIndex, match.index));
    const category = HIGHLIGHT_MAP.get(match[0].toLowerCase()) || "visibility";
    html += `<mark class="story-mark ${category}">${escapeHtml(match[0])}</mark>`;
    lastIndex = match.index + match[0].length;
  }

  html += escapeHtml(text.slice(lastIndex));
  return html;
}

function highlightStoryText(text) {
  const marked = markImportantPhrases(text);
  return marked
    .replace(/“([^”]+)”/g, '<span class="spoken">“$1”</span>')
    .replace(/^([A-Za-z]+:)/, '<span class="spoken">$1</span>');
}

function stepScene(delta) {
  const next = state.sceneIndex + delta;
  if (next < 0 || next >= state.scenes.length) return;

  state.sceneIndex = next;
  state.speaker = "all";
  els.speakerFilter.value = "all";
  renderScene();

  const scene = state.scenes[state.sceneIndex];
  history.replaceState(null, "", sceneUrl(scene.id));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function sceneUrl(sceneId) {
  const url = new URL(location.href);
  url.searchParams.set("episode", String(state.episode));
  url.hash = `E${state.episode}-${sceneId}`;
  return url;
}

function parseLineHash() {
  const match = location.hash.match(/^#E(\d+)-(L\d{3})$/i);
  if (!match) return null;
  return { episode: Number(match[1]), id: match[2].toUpperCase() };
}

function parseSceneHash() {
  const match = location.hash.match(/^#E(\d+)-(scene-\d{2})$/i);
  if (!match) return null;
  return { episode: Number(match[1]), id: match[2].toLowerCase() };
}

function applyHashSelection() {
  const line = parseLineHash();
  const sceneHash = parseSceneHash();

  if (line && line.episode === state.episode) {
    const idx = state.scenes.findIndex(scene => scene.lines.some(item => item.id === line.id));
    if (idx >= 0) state.sceneIndex = idx;
  } else if (sceneHash && sceneHash.episode === state.episode) {
    const idx = state.scenes.findIndex(scene => scene.id === sceneHash.id);
    if (idx >= 0) state.sceneIndex = idx;
  }
}

async function handleHashChange() {
  const line = parseLineHash();
  const sceneHash = parseSceneHash();
  const parsed = line || sceneHash;
  if (!parsed) return;

  if (parsed.episode !== state.episode && EPISODES[parsed.episode]) {
    await loadEpisode(parsed.episode, false);
  } else {
    applyHashSelection();
    renderScene();
  }

  if (line) requestAnimationFrame(() => scrollToLine(line.id, true));
}

function scrollToLine(id, smooth) {
  const node = document.getElementById(`E${state.episode}-${id}`);
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
