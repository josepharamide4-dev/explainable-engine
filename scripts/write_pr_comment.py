import json
from pathlib import Path

from core.pr_comment import render_pr_comment


def main():
    check_path = Path("explainable-check.json")
    output_path = Path("explainable-pr-comment.md")

    if not check_path.exists():
        raise FileNotFoundError("Missing explainable-check.json")

    payload = json.loads(check_path.read_text(encoding="utf-8"))
    comment = render_pr_comment(payload)

    output_path.write_text(comment, encoding="utf-8")
    print(f"Wrote PR comment to: {output_path}")


if __name__ == "__main__":
    main()
