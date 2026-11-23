"""Teacher/admin helper.   python scripts/admin.py list | remove NICK | reset"""
import sys
from common import load, save

cmd, args = (sys.argv[1] if len(sys.argv) > 1 else ""), sys.argv[2:]
data = load()
if cmd == "list":
    for e in data["entries"]:
        print(f"{e['difficulty']:8} {e['nick']:26} best {e['best']:4}  plays {e['plays']}")
    print(len(data["entries"]), "entries")
elif cmd == "remove" and args:
    before = len(data["entries"])
    data["entries"] = [e for e in data["entries"] if e["nick"].lower() != args[0].lower()]
    save(data); print("Removed", before - len(data["entries"]), "entries for", args[0])
elif cmd == "reset":
    save({"entries": []}); print("Leaderboard cleared.")
else:
    print(__doc__)
