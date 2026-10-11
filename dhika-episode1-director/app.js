const DATA = window.EPISODE_ONE_DIRECTOR_DATA;

const state = {
  lines: [],
  activeBlockId: DATA.blocks[0].id,
  relation: "all",
  query: "",
  hits: [],
  hitIndex: -1,
};

const $ = (id) => document.getElementById(id);

const refsToRange = (startRef, endRef = startRef) => {
  const read = (ref) => Number.parseInt(ref.split("-L")[1], 10);
  return [read(startRef), read(endRef)];
};

const lineInRanges = (lineNo, refs) =>
  refs.some(([start, end]) => {
    const [from, to] = refsToRange(start, end);
    return lineNo >= from && lineNo <= to;
  });

const claimForLine = (lineNo) =>
  DATA.claims.filter((claim) =>
    claim.refs.some((ref) => {
      const [from, to] = refsToRange(ref, ref);
      return lineNo >= from && lineNo <= to;
    })
  );

function extractEpisode(rawText, episodeNumber) {
  const lines = rawText.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
  const marker = `EPISODE ${episodeNumber}`;
  const start = lines.findIndex((line) => line.trim() === marker);
  if (start === -1) {
    throw new Error(`${marker} not found in loaded RAW.`);
  }

  const next = lines.findIndex((line, index) => {
    if (index <= start) return false;
    return /^EPISODE\s+\d+$/i.test(line.trim());
  });

  let block = lines.slice(start, next === -1 ? lines.length : next);
  while (block.length > 0) {
    const tail = block[block.length - 1].trim();
    if (tail === "" || /^=+$/.test(tail)) block.pop();
    else break;
  }

  return block.map((text, index) => ({
    number: index + 1,
    ref: `E${String(episodeNumber).padStart(2, "0")}-L${String(index + 1).padStart(3, "0")}`,
    text,
  }));
}

function setStatus(message, kind = "ok") {
  const box = $("loadStatus");
  box.textContent = message;
  box.className = `status ${kind}`;
}

async function loadFile(file) {
  const text = await file.text();
  loadRawText(text, file.name);
}

function loadRawText(text, label = "pasted RAW") {
  try {
    state.lines = extractEpisode(text, 1);
    state.hitIndex = -1;
    setStatus(`Loaded ${state.lines.length} Episode 01 lines from ${label}.`, "ok");
    renderAll();
  } catch (error) {
    state.lines = [];
    setStatus(error.message, "error");
    renderAll();
  }
}

function formatRefList(refs) {
  return refs.map(([start, end]) => (start === end ? start : `${start} to ${end}`)).join(", ");
}

function renderFilters() {
  const select = $("relationFilter");
  const current = select.value || "all";
  const relations = Array.from(new Set(DATA.blocks.map((block) => block.relation))).sort();
  select.innerHTML = `<option value="all">All characters</option>${relations
    .map((relation) => `<option value="${relation}">${relation}</option>`)
    .join("")}`;
  select.value = relations.includes(current) ? current : "all";
}

function renderBlocks() {
  const list = $("blockList");
  const visible = DATA.blocks.filter((block) => state.relation === "all" || block.relation === state.relation);
  list.innerHTML = visible
    .map((block) => {
      const active = block.id === state.activeBlockId ? " active" : "";
      const status = block.status === "locked" ? "locked" : "ask author";
      return `
        <button class="block-card${active}" data-block-id="${block.id}" type="button">
          <span class="pill ${block.status}">${status}</span>
          <strong>${block.title}</strong>
          <span>${block.actors.join(", ")}</span>
          <small>${formatRefList(block.refs)}</small>
        </button>
      `;
    })
    .join("");
}

function renderRawLines() {
  const container = $("rawLines");
  const selected = DATA.blocks.find((block) => block.id === state.activeBlockId);
  const onlySelected = $("showOnlySelected").checked;
  const showClaims = $("showClaims").checked;
  const q = state.query.trim().toLowerCase();
  state.hits = [];

  if (!state.lines.length) {
    container.className = "raw-lines empty-state";
    container.textContent = "No RAW loaded yet.";
    $("readerHint").textContent = "Load the RAW file to see exact line text.";
    return;
  }

  const rows = state.lines.filter((line) => {
    const selectedMatch = selected ? lineInRanges(line.number, selected.refs) : false;
    const queryMatch = !q || line.ref.toLowerCase().includes(q) || line.text.toLowerCase().includes(q);
    if (queryMatch && q) state.hits.push(line.ref);
    return queryMatch && (!onlySelected || selectedMatch);
  });

  $("readerHint").textContent = selected
    ? `Selected: ${selected.title} (${formatRefList(selected.refs)})`
    : "Episode 01 loaded.";

  container.className = "raw-lines";
  container.innerHTML = rows
    .map((line) => {
      const selectedMatch = selected ? lineInRanges(line.number, selected.refs) : false;
      const claims = showClaims ? claimForLine(line.number) : [];
      const hit = q && (line.ref.toLowerCase().includes(q) || line.text.toLowerCase().includes(q));
      return `
        <article id="${line.ref}" class="raw-row${selectedMatch ? " selected" : ""}${hit ? " hit" : ""}">
          <div class="raw-ref">${line.ref}</div>
          <div class="raw-text">${escapeHtml(line.text) || "&nbsp;"}</div>
          ${
            claims.length
              ? `<div class="line-claims">${claims
                  .map((claim) => `<span class="mini ${claim.status}">${claim.status}</span>`)
                  .join("")}</div>`
              : ""
          }
        </article>
      `;
    })
    .join("");
}

function renderClaims() {
  $("claimsTab").innerHTML = DATA.claims
    .map(
      (claim) => `
        <article class="note-card">
          <span class="pill ${claim.status}">${claim.status === "locked" ? "locked" : "ask author"}</span>
          <h3>${claim.title}</h3>
          <p>${claim.text}</p>
          <button type="button" data-jump-ref="${claim.refs[0]}">${claim.refs.join(", ")}</button>
        </article>
      `
    )
    .join("");

  $("carryTab").innerHTML = DATA.carryForward
    .map(
      (item) => `
        <article class="note-card">
          <span class="pill locked">carry</span>
          <h3>${item.title}</h3>
          <p>${item.rule}</p>
          <button type="button" data-jump-ref="${item.refs[0]}">${item.refs.join(", ")}</button>
        </article>
      `
    )
    .join("");

  $("questionsTab").innerHTML = DATA.questions
    .map(
      (item) => `
        <article class="note-card ask">
          <span class="pill ask-author">ask before directing</span>
          <h3>${item.title}</h3>
          <p>${item.reason}</p>
          <button type="button" data-jump-ref="${item.refs[0]}">${item.refs.join(", ")}</button>
        </article>
      `
    )
    .join("");

  $("guardTab").innerHTML = DATA.guardRules
    .map(
      (rule) => `
        <article class="note-card">
          <span class="pill guard">guard</span>
          <h3>${rule.title}</h3>
          <p>${rule.check}</p>
        </article>
      `
    )
    .join("");
}

function renderMetrics() {
  $("lineCount").textContent = state.lines.length;
  $("blockCount").textContent = DATA.blocks.length;
  $("lockedCount").textContent = DATA.claims.filter((claim) => claim.status === "locked").length;
}

function renderAll() {
  renderFilters();
  renderBlocks();
  renderClaims();
  renderRawLines();
  renderMetrics();
}

function jumpToRef(ref) {
  $("showOnlySelected").checked = false;
  state.query = ref;
  $("searchInput").value = ref;
  renderRawLines();
  const target = document.getElementById(ref);
  if (target) target.scrollIntoView({ behavior: "smooth", block: "center" });
}

function moveHit(delta) {
  if (!state.hits.length) return;
  state.hitIndex = (state.hitIndex + delta + state.hits.length) % state.hits.length;
  const ref = state.hits[state.hitIndex];
  const target = document.getElementById(ref);
  if (target) target.scrollIntoView({ behavior: "smooth", block: "center" });
}

function copyDirectorPacket() {
  const packet = {
    version: DATA.version,
    episode: 1,
    selectedBlock: state.activeBlockId,
    claims: DATA.claims,
    carryForward: DATA.carryForward,
    askAuthor: DATA.questions,
    guardRules: DATA.guardRules,
  };
  navigator.clipboard.writeText(JSON.stringify(packet, null, 2)).then(() => {
    setStatus("Director packet copied with refs and ask-author gates.", "ok");
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

document.addEventListener("click", (event) => {
  const blockButton = event.target.closest("[data-block-id]");
  if (blockButton) {
    state.activeBlockId = blockButton.dataset.blockId;
    renderBlocks();
    renderRawLines();
    return;
  }

  const jumpButton = event.target.closest("[data-jump-ref]");
  if (jumpButton) {
    jumpToRef(jumpButton.dataset.jumpRef);
    return;
  }

  const tab = event.target.closest(".tab");
  if (tab) {
    document.querySelectorAll(".tab").forEach((button) => button.classList.remove("active"));
    document.querySelectorAll(".tab-page").forEach((page) => page.classList.remove("active"));
    tab.classList.add("active");
    $(`${tab.dataset.tab}Tab`).classList.add("active");
  }
});

$("rawFileInput").addEventListener("change", (event) => {
  const file = event.target.files?.[0];
  if (file) loadFile(file);
});

$("loadPasteBtn").addEventListener("click", () => {
  const text = $("rawPaste").value.trim();
  if (!text) {
    setStatus("Paste RAW text first.", "error");
    return;
  }
  loadRawText(text, "pasted RAW");
});

$("clearBtn").addEventListener("click", () => {
  state.lines = [];
  state.query = "";
  $("searchInput").value = "";
  $("rawPaste").value = "";
  $("rawFileInput").value = "";
  setStatus("RAW cleared. Source map is still ready.", "warn");
  renderAll();
});

$("copyPacketBtn").addEventListener("click", copyDirectorPacket);
$("relationFilter").addEventListener("change", (event) => {
  state.relation = event.target.value;
  renderBlocks();
});
$("searchInput").addEventListener("input", (event) => {
  state.query = event.target.value;
  state.hitIndex = -1;
  renderRawLines();
});
$("showOnlySelected").addEventListener("change", renderRawLines);
$("showClaims").addEventListener("change", renderRawLines);
$("prevHitBtn").addEventListener("click", () => moveHit(-1));
$("nextHitBtn").addEventListener("click", () => moveHit(1));

renderAll();
