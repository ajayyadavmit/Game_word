"""Run by GitHub Actions: read a SCORE issue, update leaderboard.json, report the result."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load, save, add_score


def out(msg, accepted):
    print(msg)
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(f"accepted={str(accepted).lower()}\n")
            f.write("msg=" + msg + "\n")


body = os.environ.get("ISSUE_BODY", "")
m = re.search(r"\{[^{}]*\}", body)
try:
    if not m:
        raise ValueError("no score found in the issue")
    data = load()
    e = add_score(data, json.loads(m.group(0)))
    save(data)
    out(f"Score added. {e['nick']} best score is now {e['best']}.", True)
except ValueError as err:          # includes JSON errors
    out(f"Score not added: {err}", False)
