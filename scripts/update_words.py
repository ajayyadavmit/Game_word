"""Run by GitHub Actions: add words with hints and meanings to words.json.
Uses Claude if ANTHROPIC_API_KEY is set, otherwise Datamuse and Dictionary API."""
import json, os, re, sys, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CFG

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "words.json")
LO, HI = CFG["wordLength"]["min"], CFG["wordLength"]["max"]
domain = re.sub(r"\s+", "_", os.environ.get("DOMAIN", "").strip().lower())
query = os.environ.get("QUERY", "").strip()
count = max(1, min(int(os.environ.get("COUNT") or 20), 100))
if not re.fullmatch(r"[a-z0-9_-]{2,20}", domain) or not query:
    sys.exit("DOMAIN must be 2-20 letters/digits, underscores, or hyphens; QUERY must not be empty")


def from_claude(key):
    prompt = (f"List {count} single English words for a spelling game about: {query}. "
              f"Letters A-Z only, {LO} to {HI} letters, suitable for school students, no proper nouns. "
              "For each word provide a short clue suitable before the answer and a clear dictionary-style "
              "meaning suitable after the answer. Reply only with a JSON array of objects, each having "
              '"word", "hint", and "meaning" string fields.')
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({"model": os.environ.get("MODEL") or "claude-sonnet-5-5", "max_tokens": min(count * 120, 12000),
                         "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = "".join(b.get("text", "") for b in json.load(r)["content"])
    return json.loads(text[text.index("["):text.rindex("]") + 1])


def datamuse_request(parameter):
    url = "https://api.datamuse.com/words?" + urllib.parse.urlencode({parameter: query, "max": count * 5})
    with urllib.request.urlopen(url, timeout=30) as r:
        return [w["word"] for w in json.load(r)]


def from_datamuse():
    found = datamuse_request("topics")
    if found:
        return found
    print("Datamuse topics search returned no matches; retrying with meaning-related search.")
    return datamuse_request("ml")


def dictionary_details(word):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word.lower())}"
    req = urllib.request.Request(url, headers={"User-Agent": "Word-Fix educational word game"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            entries = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    for entry in entries:
        for part in entry.get("meanings", []):
            for definition in part.get("definitions", []):
                text = definition.get("definition", "").strip()
                if text:
                    return {"hint": text, "meaning": text}
    return None


key = os.environ.get("ANTHROPIC_API_KEY")
print("Using Claude word generation." if key else "ANTHROPIC_API_KEY is not set; using Datamuse.")
found = from_claude(key) if key else from_datamuse()

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)
existing = data.get(domain, [])
if not isinstance(existing, list):
    sys.exit(f"words.json topic '{domain}' must contain a list")
have = {(x["word"] if isinstance(x, dict) else x).upper() for x in existing}
added = []
for candidate in found:
    record = candidate if isinstance(candidate, dict) else {"word": candidate}
    w = str(record.get("word", "")).strip().upper()
    if not re.fullmatch(rf"[A-Z]{{{LO},{HI}}}", w) or w in have or len(added) >= count:
        continue
    details = dictionary_details(w) if not record.get("hint") or not record.get("meaning") else None
    if details is None and (not record.get("hint") or not record.get("meaning")):
        print(f"Skipping {w}: no dictionary definition found.")
        continue
    hint = str(record.get("hint") or (details or {}).get("hint", "")).strip()
    meaning = str(record.get("meaning") or (details or {}).get("meaning", "")).strip()
    if not hint or not meaning:
        print(f"Skipping {w}: a hint and meaning could not be created.")
        continue
    have.add(w)
    source = "AI-generated (Claude)" if record.get("meaning") else "Free Dictionary API (dictionaryapi.dev)"
    added.append({"word": w, "hint": hint, "meaning": meaning, "meaningSource": source})
if not added:
    sys.exit(f"No new usable words with hints and meanings found for '{domain}'. words.json was not changed.")
data[domain] = existing + added
with open(PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
print(f"Added {len(added)} words to '{domain}':", ", ".join(item["word"] for item in added))
