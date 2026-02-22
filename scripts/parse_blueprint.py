#!/usr/bin/env python3
"""Parse a blueprint markdown file into structured JSON.

Extracts phases, tasks, dependencies, affected files, and verification commands
from the canonical blueprint format.

Usage:
    python3 parse_blueprint.py <blueprint.md>
    python3 parse_blueprint.py <blueprint.md> --phases-only
    python3 parse_blueprint.py <blueprint.md> --files-only
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def parse_metadata(content: str) -> dict:
    """Extract metadata from the blueprint header block."""
    meta = {}
    for pattern, key in [
        (r">\s*\*\*Status\*\*:\s*(.+)", "status"),
        (r">\s*\*\*Created\*\*:\s*(.+)", "created"),
        (r">\s*\*\*Blueprint ID\*\*:\s*(.+)", "id"),
        (r">\s*\*\*Source\*\*:\s*(.+)", "source"),
    ]:
        m = re.search(pattern, content)
        if m:
            meta[key] = m.group(1).strip()

    # Title from first H1
    m = re.search(r"^#\s+Blueprint:\s*(.+)", content, re.MULTILINE)
    if m:
        meta["title"] = m.group(1).strip()

    return meta


def parse_affected_files(content: str) -> list[dict]:
    """Extract the affected files table."""
    files = []
    # Match markdown table rows: | # | Op | File Path | Phase | Description |
    in_table = False
    for line in content.split("\n"):
        if "| Op |" in line or "| op |" in line.lower():
            in_table = True
            continue
        if in_table and line.strip().startswith("|---"):
            continue
        if in_table and line.strip().startswith("|"):
            cols = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cols) >= 5:
                files.append({
                    "num": cols[0],
                    "op": cols[1],
                    "path": cols[2],
                    "phase": cols[3],
                    "description": cols[4],
                })
        elif in_table and not line.strip().startswith("|"):
            in_table = False

    return files


def parse_phases(content: str) -> list[dict]:
    """Extract phases with their tasks, dependencies, and verification."""
    phases = []
    # Split by ### Phase N: Title
    phase_pattern = re.compile(
        r"###\s+Phase\s+(\d+):\s*(.+?)(?=\n###\s+Phase\s+\d+:|\n##\s+[^#]|\Z)",
        re.DOTALL,
    )

    for m in phase_pattern.finditer(content):
        num = int(m.group(1))
        title = m.group(2).split("\n")[0].strip()
        body = m.group(2)

        phase: dict = {"num": num, "title": title, "tasks": []}

        # Extract fields
        for field, key in [
            (r"\*\*Goal\*\*:\s*(.+)", "goal"),
            (r"\*\*Dependencies\*\*:\s*(.+)", "dependencies"),
            (r"\*\*Done criteria\*\*:\s*(.+)", "done_criteria"),
            (r"\*\*Verification\*\*:\s*(.+)", "verification"),
            (r"\*\*Estimated scope\*\*:\s*(.+)", "estimated_scope"),
        ]:
            fm = re.search(field, body)
            if fm:
                phase[key] = fm.group(1).strip()

        # Extract tasks (checkbox items)
        for tm in re.finditer(r"-\s+\[([x ])\]\s+(\d+\.\d+):\s*(.+)", body):
            phase["tasks"].append({
                "id": tm.group(2),
                "description": tm.group(3).strip(),
                "done": tm.group(1) == "x",
            })

        phases.append(phase)

    return phases


def parse_cross_cutting(content: str) -> list[dict]:
    """Extract cross-cutting concerns."""
    concerns = []
    section = re.search(
        r"##\s+Cross-cutting Concerns\s*\n(.+?)(?=\n##\s|\Z)", content, re.DOTALL
    )
    if section:
        for m in re.finditer(
            r"-\s+\[([x ])\]\s+\*\*(.+?)\*\*:\s*(.+)", section.group(1)
        ):
            concerns.append({
                "name": m.group(2),
                "description": m.group(3).strip(),
                "resolved": m.group(1) == "x",
            })
    return concerns


def parse_risks(content: str) -> list[dict]:
    """Extract risk assessment table."""
    risks = []
    in_table = False
    for line in content.split("\n"):
        if "| Risk |" in line:
            in_table = True
            continue
        if in_table and line.strip().startswith("|---"):
            continue
        if in_table and line.strip().startswith("|"):
            cols = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cols) >= 4:
                risks.append({
                    "risk": cols[0],
                    "impact": cols[1],
                    "likelihood": cols[2],
                    "mitigation": cols[3],
                })
        elif in_table and not line.strip().startswith("|"):
            in_table = False
    return risks


def parse_verification_checklist(content: str) -> list[dict]:
    """Extract final verification checklist."""
    items = []
    section = re.search(
        r"##\s+Final Verification Checklist\s*\n(.+?)(?=\n##\s|\Z)",
        content,
        re.DOTALL,
    )
    if section:
        for m in re.finditer(r"-\s+\[([x ])\]\s+(.+)", section.group(1)):
            items.append({
                "description": m.group(2).strip(),
                "done": m.group(1) == "x",
            })
    return items


def parse_blueprint(path: str) -> dict:
    """Parse a complete blueprint file into structured data."""
    content = Path(path).read_text()
    return {
        "metadata": parse_metadata(content),
        "affected_files": parse_affected_files(content),
        "phases": parse_phases(content),
        "cross_cutting": parse_cross_cutting(content),
        "risks": parse_risks(content),
        "verification_checklist": parse_verification_checklist(content),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: parse_blueprint.py <blueprint.md> [--phases-only|--files-only]")
        sys.exit(1)

    path = sys.argv[1]
    if not Path(path).exists():
        print(f"Error: {path} not found", file=sys.stderr)
        sys.exit(1)

    result = parse_blueprint(path)

    if "--phases-only" in sys.argv:
        print(json.dumps(result["phases"], indent=2))
    elif "--files-only" in sys.argv:
        print(json.dumps(result["affected_files"], indent=2))
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
