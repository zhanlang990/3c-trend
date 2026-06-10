"""Export user feedback from the frontend localStorage to data/feedback.json.

Usage:
  python crawler/export_feedback.py <feedback_json_string>

The frontend should collect localStorage["safebox_feedback_v1"]
and pass it as a JSON string argument. This script writes it to
data/feedback.json for the crawler to read on next run.

Alternatively, if run with no arguments, it creates an empty
feedback.json file (useful for first-time setup).
"""
import json
import os
import sys

CURDIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CURDIR)
FEEDBACK_PATH = os.path.join(ROOT, "data", "feedback.json")


def export_feedback(json_str=None):
    """Write feedback data to data/feedback.json.

    Args:
        json_str: JSON string of {url: "good"|"bad"} mapping.
                  If None, writes empty dict.
    """
    if json_str:
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Error: invalid JSON input: {e}", file=sys.stderr)
            sys.exit(1)
        # Validate structure
        if not isinstance(data, dict):
            print("Error: feedback must be a JSON object {url: vote}", file=sys.stderr)
            sys.exit(1)
        for url, vote in data.items():
            if vote not in ("good", "bad", ""):
                print(f"Warning: skipping invalid vote '{vote}' for {url}", file=sys.stderr)
        # Clean empty votes
        data = {k: v for k, v in data.items() if v in ("good", "bad")}
    else:
        data = {}

    os.makedirs(os.path.dirname(FEEDBACK_PATH), exist_ok=True)
    with open(FEEDBACK_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(data)} feedback entries to {FEEDBACK_PATH}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        export_feedback(sys.argv[1])
    else:
        export_feedback()