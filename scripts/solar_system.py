#!/usr/bin/env python3
"""Render an ASCII solar system where planets are GitHub projects.

The sun sits in the center. Each repository orbits at its own radius and
period. The renderer samples the positions for the current UTC date, then
splices the ASCII art back into README.md between the SOLAR_SYSTEM markers.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

GITHUB_USER = os.environ.get("SOLAR_SYSTEM_USER", "streed")
README_PATH = Path(__file__).resolve().parent.parent / "README.md"

WIDTH = 92
HEIGHT = 35
CX = WIDTH // 2
CY = HEIGHT // 2

# (rx, ry, period_in_days) for each orbit, inner -> outer.
ORBITS = [
    (9, 3, 36),
    (16, 6, 72),
    (23, 9, 132),
    (30, 12, 220),
    (37, 15, 340),
    (44, 17, 500),
]

PLANET_GLYPHS = ["o", "O", "@", "#", "*", "%"]

EPOCH = dt.date(2024, 1, 1)


@dataclass
class Project:
    name: str
    description: str
    url: str
    stars: int


def fetch_projects() -> list[Project]:
    url = f"https://api.github.com/users/{GITHUB_USER}/repos?per_page=100&type=owner"
    req = urllib.request.Request(url, headers={"User-Agent": "ascii-solar-system"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as exc:
        print(f"warning: could not fetch repos ({exc}); using fallback", file=sys.stderr)
        return fallback_projects()

    repos = [
        r for r in data
        if not r.get("fork")
        and not r.get("archived")
        and not r.get("private")
        and r.get("name") != GITHUB_USER
    ]
    repos.sort(
        key=lambda r: (r.get("stargazers_count", 0), r.get("pushed_at", "")),
        reverse=True,
    )
    picks = repos[: len(ORBITS)]
    return [
        Project(
            name=r["name"],
            description=(r.get("description") or "").strip(),
            url=r["html_url"],
            stars=r.get("stargazers_count", 0),
        )
        for r in picks
    ]


def fallback_projects() -> list[Project]:
    return [
        Project(name=f"project-{i+1}", description="", url="", stars=0)
        for i in range(len(ORBITS))
    ]


def plot_orbit(grid: list[list[str]], rx: int, ry: int) -> None:
    steps = max(360, 8 * (rx + ry))
    for i in range(steps):
        theta = 2 * math.pi * i / steps
        x = int(round(CX + rx * math.cos(theta)))
        y = int(round(CY + ry * math.sin(theta)))
        if 0 <= x < WIDTH and 0 <= y < HEIGHT and grid[y][x] == " ":
            grid[y][x] = "."


def draw_sun(grid: list[list[str]]) -> None:
    art = [
        r" \ | / ",
        r"--(*)--",
        r" / | \ ",
    ]
    for dy, line in enumerate(art):
        y = CY - 1 + dy
        for dx, ch in enumerate(line):
            if ch == " ":
                continue
            x = CX - len(line) // 2 + dx
            if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                grid[y][x] = ch


def place_planet(grid: list[list[str]], glyph: str, rx: int, ry: int, angle: float) -> None:
    x = int(round(CX + rx * math.cos(angle)))
    y = int(round(CY + ry * math.sin(angle)))
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        grid[y][x] = glyph


def render(projects: list[Project], day: int) -> str:
    grid = [[" "] * WIDTH for _ in range(HEIGHT)]

    for idx in range(len(projects)):
        rx, ry, _ = ORBITS[idx]
        plot_orbit(grid, rx, ry)

    draw_sun(grid)

    for idx, project in enumerate(projects):
        rx, ry, period = ORBITS[idx]
        phase = idx * math.pi / 3
        angle = 2 * math.pi * (day % period) / period + phase
        place_planet(grid, PLANET_GLYPHS[idx % len(PLANET_GLYPHS)], rx, ry, angle)

    return "\n".join("".join(row).rstrip() for row in grid)


def build_legend(projects: list[Project]) -> str:
    rows = ["| Planet | Project | Stars | Description |", "| :---: | --- | :---: | --- |"]
    for idx, project in enumerate(projects):
        glyph = PLANET_GLYPHS[idx % len(PLANET_GLYPHS)]
        name = f"[{project.name}]({project.url})" if project.url else project.name
        desc = project.description.replace("|", "\\|") or "--"
        rows.append(f"| `{glyph}` | {name} | {project.stars} | {desc} |")
    return "\n".join(rows)


def splice_readme(art: str, legend: str, today: dt.date) -> None:
    begin = "<!-- SOLAR_SYSTEM_START -->"
    end = "<!-- SOLAR_SYSTEM_END -->"
    original = README_PATH.read_text()
    if begin not in original or end not in original:
        raise SystemExit(
            f"README.md is missing {begin} / {end} markers; cannot update solar system."
        )

    block = (
        f"{begin}\n"
        f"### My Solar System of Projects\n\n"
        f"```\n{art}\n```\n\n"
        f"{legend}\n\n"
        f"_Orbits refreshed daily by GitHub Actions -- last update {today.isoformat()} UTC._\n"
        f"{end}"
    )
    pre, _, rest = original.partition(begin)
    _, _, post = rest.partition(end)
    README_PATH.write_text(pre + block + post)


def main() -> int:
    today = dt.datetime.now(dt.timezone.utc).date()
    day = (today - EPOCH).days
    projects = fetch_projects()
    if not projects:
        projects = fallback_projects()
    art = render(projects, day)
    legend = build_legend(projects)
    splice_readme(art, legend, today)
    print(f"Updated solar system for {today.isoformat()} with {len(projects)} planets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
