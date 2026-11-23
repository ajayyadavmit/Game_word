"""Run by GitHub Actions: add words for one domain to words.json.
Uses Claude if ANTHROPIC_API_KEY is set, otherwise the free Datamuse word API."""
import json, os, re, sys, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CFG

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "words.json")
LO, HI = CFG["wordLength"]["min"], CFG["wordLength"]["max"]
domain = os.environ.get("DOMAIN", "").strip().lower()
query = os.environ.get("QUERY", "").strip()
count = max(1, min(int(os.environ.get("COUNT") or 20), 100))
if not re.fullmatch(r"[a-z0-9_-]{2,20}", domain) or not query:
    sys.exit("DOMAIN must be 2-20 letters/digits and QUERY must not be empty")


def from_claude(key):
    prompt = (f"List {count} single English words for a spelling game about: {query}. "
              f"Letters A-Z only, {LO} to {HI} letters, suitable for school students, no proper nouns. "
              "Reply with a JSON array of strings and nothing else.")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({"model": os.environ.get("MODEL") or "claude-sonnet-5-5", "max_tokens": 1000,
                         "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = "".join(b.get("text", "") for b in json.load(r)["content"])
    return json.loads(text[text.index("["):text.rindex("]") + 1])


def from_datamuse():
    url = "https://api.datamuse.com/words?" + urllib.parse.urlencode({"topics": query, "max": count * 5})
    with urllib.request.urlopen(url, timeout=30) as r:
        return [w["word"] for w in json.load(r)]


key = os.environ.get("ANTHROPIC_API_KEY")
found = from_claude(key) if key else from_datamuse()

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)
have = {(x["word"] if isinstance(x, dict) else x).upper() for x in data.setdefault(domain, [])}
added = []
for w in found:
    w = str(w).strip().upper()
    if re.fullmatch(rf"[A-Z]{{{LO},{HI}}}", w) and w not in have and len(added) < count:
        have.add(w); added.append(w)
data[domain] += added
with open(PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
print(f"Added {len(added)} words to '{domain}':", ", ".join(added))
