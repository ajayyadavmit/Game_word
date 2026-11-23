"use strict";
// All settings live in config.json. Words live in words.json.
const $ = id => document.getElementById(id);
const rnd = n => Math.floor(Math.random() * n);
const shuffle = a => { for (let i = a.length - 1; i > 0; i--) { const j = rnd(i + 1); [a[i], a[j]] = [a[j], a[i]]; } return a; };
function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; }
async function getJSON(url) { const r = await fetch(url, { cache: "no-store" }); if (!r.ok) throw new Error(url + " not found"); return r.json(); }

let CFG, mode = "github", bank = {}, allWords = new Set(), nick = "", level = "", boardLevel = "", boardData = [], boardFailed = false, game = null;
try { nick = localStorage.getItem("wg_nick") || ""; } catch (e) {}

// ---------- guest nickname (suggested by the program, no free typing) ----------
function suggestNames() {
  const { adjectives: A, animals: N, suggestionsShown: k } = CFG.nicknames, s = new Set();
  for (let g = 0; s.size < k && g < 200; g++) s.add(A[rnd(A.length)] + N[rnd(N.length)] + (10 + rnd(90)));
  return [...s];
}
function markNick() {
  for (const b of $("nicks").children) { const on = b.textContent === nick; b.classList.toggle("on", on); b.setAttribute("aria-pressed", String(on)); }
  updatePlay();
}
function renderNicks() {
  const box = $("nicks"); box.innerHTML = "";
  [...new Set([...(nick ? [nick] : []), ...suggestNames()])].slice(0, CFG.nicknames.suggestionsShown).forEach(n => {
    const b = el("button", "chip", n); b.type = "button";
    b.onclick = () => { nick = n; try { localStorage.setItem("wg_nick", n); } catch (e) {} markNick(); };
    box.appendChild(b);
  });
  markNick();
}

// ---------- words ----------
function loadWords(json) {
  bank = {}; allWords = new Set();
  const { min, max } = CFG.wordLength, ok = new RegExp(`^[A-Z]{${min},${max}}$`);
  for (const [d, list] of Object.entries(json)) {
    const seen = new Set(), items = [];
    for (const raw of list || []) {
      const obj = raw && typeof raw === "object";
      const w = String(obj ? raw.word : raw).trim().toUpperCase(), hint = obj && raw.hint ? String(raw.hint) : "";
      if (!ok.test(w)) console.warn(`Skipped "${w}" in "${d}": use letters A-Z only, ${min}-${max} letters long.`);
      else if (!seen.has(w)) { seen.add(w); items.push({ w, hint }); allWords.add(w); }
    }
    if (items.length) bank[d.toLowerCase()] = items;
  }
  if (!allWords.size) throw new Error("words.json has no usable words");
}
// A word is playable at a level only if its first and last letters can stay visible.
function pool(domain, lv) {
  const need = CFG.difficulties[lv].blanks + 2, seen = new Map();
  (domain === "all" ? Object.values(bank).flat() : bank[domain] || []).forEach(x => { if (x.w.length >= need && !seen.has(x.w)) seen.set(x.w, x); });
  return [...seen.values()];
}
function refreshTopics() {
  const s = $("domain"), keep = s.value || "all"; s.innerHTML = "";
  s.add(new Option(`All topics (${pool("all", level).length})`, "all"));
  for (const d of Object.keys(bank)) s.add(new Option(`${d} (${pool(d, level).length})`, d));
  s.value = [...s.options].some(o => o.value === keep) ? keep : "all";
  updatePlay();
}
function updatePlay() {
  const n = pool($("domain").value || "all", level).length;
  $("play").disabled = !nick || n === 0;
  $("playinfo").textContent = n ? `${Math.min(n, CFG.rounds)} words this game` : "No words fit this topic at this level. Add longer words to words.json.";
}

// APPLE with 2 blanks becomes A__LE. The hidden letters are always one block.
function makeQuestion(word, hide) {
  const n = word.length, start = 1 + rnd(n - hide - 1);
  const pre = word.slice(0, start), post = word.slice(start + hide), correct = word.slice(start, start + hide);
  const V = "AEIOU", C = "BCDFGHJKLMNPQRSTVWXYZ", wrong = new Set();
  for (let t = 0; wrong.size < CFG.optionsPerQuestion - 1 && t < 300; t++) {
    const ch = [...correct];
    const swap = i => { const p = V.includes(ch[i]) ? V : C; ch[i] = p[rnd(p.length)]; };
    swap(rnd(ch.length));
    if (ch.length > 1 && Math.random() < 0.4) swap(rnd(ch.length));
    const c = ch.join("");
    if (c !== correct && !allWords.has(pre + c + post)) wrong.add(c);
  }
  return { word, correct, shown: pre + "_".repeat(hide) + post, options: shuffle([correct, ...wrong]) };
}

// ---------- levels ----------
function markLevel() { for (const b of $("levels").children) { const on = b.dataset.k === level; b.classList.toggle("on", on); b.setAttribute("aria-pressed", String(on)); } }
function markTab() { for (const b of $("tabs").children) { const on = b.dataset.k === boardLevel; b.classList.toggle("on", on); b.setAttribute("aria-pressed", String(on)); } }
function renderLevels() {
  for (const [k, d] of Object.entries(CFG.difficulties)) {
    const b = el("button", "chip seg", `${d.label} ${"_".repeat(d.blanks)}`); b.type = "button"; b.dataset.k = k;
    b.onclick = () => { level = boardLevel = k; markLevel(); markTab(); refreshTopics(); renderBoard(); };
    $("levels").appendChild(b);
    const t = el("button", "chip tab", d.label); t.type = "button"; t.dataset.k = k;
    t.onclick = () => { boardLevel = k; markTab(); renderBoard(); };
    $("tabs").appendChild(t);
  }
  markLevel(); markTab();
}

// ---------- game flow ----------
function show(id) { for (const s of ["home", "game", "end"]) $(s).hidden = s !== id; }

function start() {
  const d = $("domain").value;
  const items = shuffle(pool(d, level)).slice(0, CFG.rounds);
  game = { domain: d, level, items, i: 0, score: 0, right: 0, locked: false, q: null };
  show("game"); ask();
}

function drawTiles(word, shown, state) {
  const box = $("tiles"); box.innerHTML = "";
  [...shown].forEach((c, i) => {
    const blank = c === "_";
    box.appendChild(el("span", "tile" + (blank ? " blank" + (state ? " " + state : "") : ""), blank ? (state ? word[i] : "") : c));
  });
  box.setAttribute("aria-label", shown.replace(/_/g, " blank "));
}

function ask() {
  const item = game.items[game.i];
  const q = game.q = makeQuestion(item.w, CFG.difficulties[game.level].blanks); game.locked = false;
  $("round").textContent = `Word ${game.i + 1} of ${game.items.length}`;
  $("score").textContent = game.score;
  $("hint").textContent = item.hint ? "Hint: " + item.hint : "";
  drawTiles(q.word, q.shown);
  const box = $("opts"); box.innerHTML = "";
  q.options.forEach((o, k) => {
    const b = el("button", "opt", o); b.type = "button"; b.dataset.v = o; b.title = "Key " + (k + 1);
    b.onclick = () => answer(o); box.appendChild(b);
  });
  $("msg").textContent = ""; $("next").hidden = true;
}

function answer(o) {
  if (game.locked) return; game.locked = true;
  const q = game.q, ok = o === q.correct;
  game.score += ok ? CFG.pointsRight : CFG.pointsWrong; if (ok) game.right++;
  for (const b of $("opts").children) {
    b.disabled = true;
    if (b.dataset.v === q.correct) b.classList.add("good"); else if (b.dataset.v === o) b.classList.add("bad");
  }
  drawTiles(q.word, q.shown, ok ? "good" : "bad");
  $("score").textContent = game.score;
  $("msg").textContent = ok ? `Correct! +${CFG.pointsRight}` : `Not quite. ${CFG.pointsWrong}. The word is ${q.word}.`;
  $("next").textContent = game.i === game.items.length - 1 ? "See my score" : "Next word";
  $("next").hidden = false; $("next").focus();
}

function issueUrl(p) {
  const owner = CFG.github.owner || location.hostname.split(".")[0];
  const repo = CFG.github.repo || location.pathname.split("/")[1] || "";
  const body = "```json\n" + JSON.stringify(p) + "\n```\n\nClick **Submit new issue**. A bot adds this score to the leaderboard and closes the issue.";
  return `https://github.com/${owner}/${repo}/issues/new?title=${encodeURIComponent(`SCORE|${p.nick}|${p.score}`)}&body=${encodeURIComponent(body)}`;
}

async function finish() {
  show("end");
  $("final").textContent = game.score;
  $("summary").textContent = `${game.right} of ${game.items.length} correct. ${CFG.difficulties[game.level].label} level, ${game.domain === "all" ? "all topics" : game.domain + " topic"}.`;
  const p = { nick, score: game.score, rounds: game.items.length, difficulty: game.level, domain: game.domain };
  const msg = $("submitmsg"), btn = $("submit");
  btn.hidden = true;
  boardLevel = game.level; markTab();
  if (mode === "local") {
    try {
      const r = await fetch("api/score", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(p) });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || "server error");
      msg.textContent = "Score saved to the leaderboard.";
    } catch (e) { msg.textContent = "Could not save your score: " + e.message; }
    loadBoard();
  } else {
    msg.textContent = "To join the shared leaderboard, send your score. This needs a free GitHub account.";
    btn.hidden = false; btn.onclick = () => window.open(issueUrl(p), "_blank", "noopener");
    renderBoard();
  }
}

// ---------- leaderboard ----------
async function loadBoard() {
  try { boardData = (await getJSON("leaderboard.json?t=" + Date.now())).entries || []; boardFailed = false; }
  catch (e) { boardData = []; boardFailed = true; }
  renderBoard();
}
function renderBoard() {
  const list = $("rows"); list.innerHTML = "";
  const rows = boardData.filter(e => e.difficulty === boardLevel).slice(0, CFG.leaderboard.showTop);
  rows.forEach(e => {
    const li = el("li", e.nick === nick ? "me" : ""); li.append(el("span", "", String(e.nick)), el("b", "", String(Number(e.best))));
    list.appendChild(li);
  });
  $("boardmsg").textContent = boardFailed ? "Leaderboard not available yet." : rows.length ? "" : "No scores yet at this level. Be the first!";
}

// ---------- start-up ----------
async function init() {
  $("play").onclick = start;
  $("domain").onchange = updatePlay;
  $("again").onclick = () => { show("home"); renderNicks(); refreshTopics(); };
  $("reroll").onclick = renderNicks;
  $("next").onclick = () => { if (game.i >= game.items.length - 1) finish(); else { game.i++; ask(); } };
  document.addEventListener("keydown", e => {
    if (!$("game").hidden && game && !game.locked && /^[1-9]$/.test(e.key)) { const b = $("opts").children[+e.key - 1]; if (b) b.click(); }
  });
  try {
    CFG = await getJSON("config.json");
    const forced = new URLSearchParams(location.search).get("mode");      // ?mode=local or ?mode=github for testing
    if (forced === "local" || forced === "github") mode = forced;
    else { try { const r = await fetch("api/ping", { cache: "no-store" }); if (r.ok && (await r.json()).ok) mode = "local"; } catch (e) {} }
    loadWords(await getJSON("words.json"));
  } catch (e) {
    const box = $("error"); box.hidden = false;
    box.textContent = "Could not load the game files (" + e.message + "). If you opened index.html by double-clicking, start the local server instead: python server.py";
    $("home").hidden = true; return;
  }
  document.title = CFG.title; $("title").textContent = CFG.title;
  const d = CFG.difficulties;
  $("rules").textContent = `Pick the missing letters to finish each word. Right answer +${CFG.pointsRight}, wrong answer ${CFG.pointsWrong}. ${CFG.rounds} words per game.`;
  level = boardLevel = d[CFG.defaultDifficulty] ? CFG.defaultDifficulty : Object.keys(d)[0];
  $("modeinfo").textContent = mode === "local" ? "Local test mode: scores save on this computer." : "Online mode: scores go through GitHub.";
  renderLevels(); renderNicks(); refreshTopics(); loadBoard();
}
init();
