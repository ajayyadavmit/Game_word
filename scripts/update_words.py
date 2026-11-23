"""Run by GitHub Actions: add words with hints and meanings to words.json.
Uses Claude if ANTHROPIC_API_KEY is set, otherwise Datamuse and Dictionary API."""
import json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CFG

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "words.json")
LO, HI = CFG["wordLength"]["min"], CFG["wordLength"]["max"]
DICTIONARY_MIN_INTERVAL = 1.0
DICTIONARY_RETRIES = 3
_last_dictionary_request = 0.0


class DictionaryRateLimitError(Exception):
    pass


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


def retry_after_seconds(error, attempt):
    value = error.headers.get("Retry-After") if error.headers else None
    if value:
        try:
            delay = float(value)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                now = datetime.now(retry_at.tzinfo or timezone.utc)
                delay = (retry_at - now).total_seconds()
            except (TypeError, ValueError, OverflowError):
                delay = 2 ** (attempt + 1)
    else:
        delay = 2 ** (attempt + 1)
    return min(max(delay, 1), 60)


def get_dictionary_entries(req):
    global _last_dictionary_request
    for attempt in range(DICTIONARY_RETRIES + 1):
        wait = DICTIONARY_MIN_INTERVAL - (time.monotonic() - _last_dictionary_request)
        if _last_dictionary_request and wait > 0:
            time.sleep(wait)
        _last_dictionary_request = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code != 429:
                raise
            if attempt == DICTIONARY_RETRIES:
                raise DictionaryRateLimitError("Dictionary API kept returning HTTP 429.") from e
            delay = retry_after_seconds(e, attempt)
            print(f"Dictionary API rate-limited the request; retrying in {delay:g} seconds.")
            time.sleep(delay)


def dictionary_details(word):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word.lower())}"
    req = urllib.request.Request(url, headers={"User-Agent": "Word-Fix educational word game"})
    entries = get_dictionary_entries(req)
    if entries is None:
        return None
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
dictionary_rate_limited = False
for candidate in found:
    record = candidate if isinstance(candidate, dict) else {"word": candidate}
    w = str(record.get("word", "")).strip().upper()
    if not re.fullmatch(rf"[A-Z]{{{LO},{HI}}}", w) or w in have or len(added) >= count:
        continue
    try:
        details = dictionary_details(w) if not record.get("hint") or not record.get("meaning") else None
    except DictionaryRateLimitError:
        print("Dictionary API remained rate-limited after retries; stopping further lookups.")
        dictionary_rate_limited = True
        break
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
    if dictionary_rate_limited:
        sys.exit("No words were added because the Dictionary API rate limit prevented looking up definitions. Retry later or configure ANTHROPIC_API_KEY.")
    sys.exit(f"No new usable words with hints and meanings found for '{domain}'. words.json was not changed.")
data[domain] = existing + added
with open(PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
print(f"Added {len(added)} words to '{domain}':", ", ".join(item["word"] for item in added))
if dictionary_rate_limited:
    print("Some requested words were not processed because the Dictionary API was rate-limited; retry later for more.")
