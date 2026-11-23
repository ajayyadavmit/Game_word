"""Process every pending SCORE issue in one serialized GitHub Actions run."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import add_score, load, save


def write_output(name, values):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        if not values:
            with open(path, "a", encoding="utf-8") as output:
                output.write(f"{name}=\n")
            return
        delimiter = f"END_{name.upper()}"
        with open(path, "a", encoding="utf-8") as output:
            output.write(f"{name}<<{delimiter}\n")
            output.write("\n".join(values) + "\n")
            output.write(f"{delimiter}\n")


def score_payload(body):
    match = re.search(r"\{[^{}]*\}", body)
    if not match:
        raise ValueError("no score found in the issue")
    return json.loads(match.group(0))


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: process_score_batch.py ISSUES_JSON")

    with open(sys.argv[1], encoding="utf-8") as source:
        issues = json.load(source)
    if not isinstance(issues, list):
        raise ValueError("GitHub issue list must be a JSON array")

    data = load()
    processed = data.setdefault("processedIssues", [])
    if not isinstance(processed, list) or any(not str(issue).isdigit() for issue in processed):
        raise ValueError("leaderboard processedIssues must be a list")
    processed = {str(issue) for issue in processed}
    accepted, rejected = [], []
    changed = False

    for issue in issues:
        if not isinstance(issue, dict) or not str(issue.get("title", "")).startswith("SCORE|"):
            continue
        issue_number = str(issue["number"])
        labels = {label.get("name") for label in issue.get("labels", []) if isinstance(label, dict)}
        if "score-rejected" in labels:
            continue
        if issue_number in processed:
            accepted.append(issue_number)
            print(f"Score issue #{issue_number} was already saved; it will be closed.")
            continue
        try:
            entry = add_score(data, score_payload(issue.get("body") or ""))
        except (ValueError, TypeError, KeyError) as error:
            rejected.append(issue_number)
            print(f"Score issue #{issue_number} rejected: {error}")
            continue

        processed.add(issue_number)
        accepted.append(issue_number)
        changed = True
        print(f"Score issue #{issue_number} accepted: {entry['nick']} best score is {entry['best']}.")

    if changed:
        data["processedIssues"] = sorted(processed, key=int)
        save(data)

    write_output("accepted_issues", accepted)
    write_output("rejected_issues", rejected)
    print(f"Processed {len(accepted)} accepted and {len(rejected)} rejected score issues.")


if __name__ == "__main__":
    main()
