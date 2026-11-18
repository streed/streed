#!/usr/bin/env python3
"""Replace the projects section of README.md with data from reedster.llc."""
import json
import re
import urllib.request
from pathlib import Path

URL = "https://reedster.llc/data/projects.json"
README = Path(__file__).resolve().parent.parent / "README.md"
START, END = "<!-- PROJECTS:START -->", "<!-- PROJECTS:END -->"


def fetch():
    with urllib.request.urlopen(URL, timeout=30) as resp:
        return json.load(resp)["data"]


def render(projects):
    live = [p for p in projects if (p.get("status") or "").lower() != "deactivated"]
    return "\n".join(
        f"- [{p['title']}]({p['githubUrl']}): {p['shortDescription']}" for p in live
    )


def main():
    block = f"{START}\n{render(fetch())}\n{END}"
    text = README.read_text()
    new, n = re.subn(f"{re.escape(START)}.*?{re.escape(END)}", lambda _: block, text, flags=re.S)
    if n != 1:
        raise SystemExit("README.md is missing the PROJECTS markers")
    README.write_text(new)


if __name__ == "__main__":
    main()
