"""Shared by server.py (local) and the GitHub Action scripts. Reads ../config.json."""
import json, os, re, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LB_PATH = os.path.join(ROOT, "leaderboard.json")
NICK = re.compile(r"^[A-Za-z0-9]{3,24}$")


def _need(ok, msg):
    if not ok:
        raise SystemExit("config.json problem: " + msg)


def _load_config():
    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as f:
        c = json.load(f)
    try:
        _need(isinstance(c["rounds"], int) and 1 <= c["rounds"] <= 100, "rounds must be 1-100")
        _need(isinstance(c["pointsRight"], int) and isinstance(c["pointsWrong"], int) and c["pointsRight"] > c["pointsWrong"],
              "pointsRight must be a whole number greater than pointsWrong")
        _need(2 <= c["optionsPerQuestion"] <= 6, "optionsPerQuestion must be 2-6")
        _need(2 <= c["wordLength"]["min"] <= c["wordLength"]["max"] <= 30, "wordLength min/max invalid")
        _need(c["difficulties"], "difficulties is empty")
        for k, d in c["difficulties"].items():
            _need(re.fullmatch(r"[a-z0-9_-]{1,20}", k), f"difficulty key '{k}' must be lowercase letters/digits")
            _need(isinstance(d["blanks"], int) and d["blanks"] >= 1 and d["label"], f"difficulty '{k}' needs label and blanks >= 1")
        _need(c["defaultDifficulty"] in c["difficulties"], "defaultDifficulty is not in difficulties")
        for w in c["nicknames"]["adjectives"] + c["nicknames"]["animals"]:
            _need(re.fullmatch(r"[A-Za-z]{2,10}", w), f"nickname word '{w}' must be 2-10 letters, no spaces")
        _need(c["leaderboard"]["storeLimitPerLevel"] >= 1 and c["leaderboard"]["showTop"] >= 1, "leaderboard sizes invalid")
    except (KeyError, TypeError):
        raise SystemExit("config.json problem: a required setting is missing or has the wrong type")
    return c


CFG = _load_config()


def load():
    try:
        with open(LB_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    if not isinstance(data.get("entries"), list):
        data["entries"] = []
    return data


def save(data):
    tmp = LB_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, LB_PATH)


def add_score(data, p):
    """Validate one finished game and update that nickname's best score at that difficulty."""
    if not isinstance(p, dict):
        raise ValueError("bad payload")
    nick, score, rounds, level = p.get("nick"), p.get("score"), p.get("rounds"), p.get("difficulty")
    if not isinstance(nick, str) or not NICK.match(nick):
        raise ValueError("bad nickname")
    if level not in CFG["difficulties"]:
        raise ValueError("bad difficulty")
    if any(isinstance(x, bool) or not isinstance(x, int) for x in (score, rounds)) or not 1 <= rounds <= CFG["rounds"]:
        raise ValueError("bad numbers")
    right, wrong = CFG["pointsRight"], CFG["pointsWrong"]
    extra = score - wrong * rounds           # only totals reachable with the scoring rules are accepted
    if extra % (right - wrong) or not 0 <= extra // (right - wrong) <= rounds:
        raise ValueError("score does not match the scoring rules")
    domain = re.sub(r"[^a-z0-9_-]", "", str(p.get("domain", "all")).lower())[:20] or "all"
    today = time.strftime("%Y-%m-%d", time.gmtime())

    entry = next((e for e in data["entries"] if e["nick"].lower() == nick.lower() and e["difficulty"] == level), None)
    if entry:
        entry["plays"] += 1
        if score > entry["best"]:
            entry["best"], entry["domain"] = score, domain
        entry["updated"] = today
    else:
        entry = {"nick": nick, "difficulty": level, "best": score, "plays": 1, "domain": domain, "updated": today}
        data["entries"].append(entry)

    data["entries"].sort(key=lambda e: (-e["best"], e["plays"]))
    count, kept = {}, []
    for e in data["entries"]:
        count[e["difficulty"]] = count.get(e["difficulty"], 0) + 1
        if count[e["difficulty"]] <= CFG["leaderboard"]["storeLimitPerLevel"]:
            kept.append(e)
    data["entries"] = kept
    return entry
