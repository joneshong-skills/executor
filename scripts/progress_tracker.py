#!/usr/bin/env python3
"""Track blueprint execution progress with persistent state.

Manages a progress.json file that records phase/task completion,
deviations, and timestamps for resume-safe execution.

Usage:
    python3 progress_tracker.py init <blueprint.md>
    python3 progress_tracker.py start-phase <blueprint-id> <phase-num>
    python3 progress_tracker.py complete-phase <blueprint-id> <phase-num>
    python3 progress_tracker.py complete-task <blueprint-id> <task-id>
    python3 progress_tracker.py deviation <blueprint-id> <phase-num> "description"
    python3 progress_tracker.py status <blueprint-id>
    python3 progress_tracker.py report <blueprint-id>
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BLUEPRINTS_DIR = Path(os.path.expanduser("~/.claude/data/blueprints"))


def _progress_path(blueprint_id: str) -> Path:
    return BLUEPRINTS_DIR / blueprint_id / "progress.json"


def _load_progress(blueprint_id: str) -> dict:
    path = _progress_path(blueprint_id)
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save_progress(blueprint_id: str, data: dict) -> None:
    path = _progress_path(blueprint_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def cmd_init(blueprint_path: str) -> None:
    """Initialize progress tracking from a blueprint file."""
    # Import the parser
    script_dir = Path(__file__).parent
    sys.path.insert(0, str(script_dir))
    from parse_blueprint import parse_blueprint

    bp = parse_blueprint(blueprint_path)
    meta = bp["metadata"]
    blueprint_id = meta.get("id", Path(blueprint_path).stem)

    progress = {
        "blueprint_id": blueprint_id,
        "blueprint_path": str(Path(blueprint_path).resolve()),
        "title": meta.get("title", ""),
        "status": "in_progress",
        "started_at": _now(),
        "completed_at": None,
        "phases": {},
        "deviations": [],
        "unplanned_work": [],
    }

    for phase in bp["phases"]:
        pnum = str(phase["num"])
        progress["phases"][pnum] = {
            "title": phase["title"],
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "dependencies": phase.get("dependencies", "none"),
            "verification": phase.get("verification", ""),
            "tasks": {
                t["id"]: {"description": t["description"], "done": False}
                for t in phase["tasks"]
            },
        }

    _save_progress(blueprint_id, progress)
    print(json.dumps({
        "action": "init",
        "blueprint_id": blueprint_id,
        "phases": len(bp["phases"]),
        "total_tasks": sum(len(p["tasks"]) for p in bp["phases"]),
        "progress_file": str(_progress_path(blueprint_id)),
    }, indent=2))


def cmd_start_phase(blueprint_id: str, phase_num: str) -> None:
    """Mark a phase as in-progress."""
    progress = _load_progress(blueprint_id)
    if phase_num not in progress.get("phases", {}):
        print(f"Error: Phase {phase_num} not found", file=sys.stderr)
        sys.exit(1)

    progress["phases"][phase_num]["status"] = "in_progress"
    progress["phases"][phase_num]["started_at"] = _now()
    _save_progress(blueprint_id, progress)
    print(f"Phase {phase_num} started: {progress['phases'][phase_num]['title']}")


def cmd_complete_phase(blueprint_id: str, phase_num: str) -> None:
    """Mark a phase as completed."""
    progress = _load_progress(blueprint_id)
    if phase_num not in progress.get("phases", {}):
        print(f"Error: Phase {phase_num} not found", file=sys.stderr)
        sys.exit(1)

    progress["phases"][phase_num]["status"] = "completed"
    progress["phases"][phase_num]["completed_at"] = _now()
    _save_progress(blueprint_id, progress)
    print(f"Phase {phase_num} completed: {progress['phases'][phase_num]['title']}")

    # Check if all phases are done
    all_done = all(
        p["status"] == "completed" for p in progress["phases"].values()
    )
    if all_done:
        progress["status"] = "completed"
        progress["completed_at"] = _now()
        _save_progress(blueprint_id, progress)
        print("All phases completed!")


def cmd_complete_task(blueprint_id: str, task_id: str) -> None:
    """Mark a specific task as done."""
    progress = _load_progress(blueprint_id)
    for pnum, phase in progress.get("phases", {}).items():
        if task_id in phase.get("tasks", {}):
            phase["tasks"][task_id]["done"] = True
            _save_progress(blueprint_id, progress)
            print(f"Task {task_id} completed")
            return

    print(f"Error: Task {task_id} not found", file=sys.stderr)
    sys.exit(1)


def cmd_deviation(blueprint_id: str, phase_num: str, description: str) -> None:
    """Log a deviation from the blueprint."""
    progress = _load_progress(blueprint_id)
    progress.setdefault("deviations", []).append({
        "phase": phase_num,
        "description": description,
        "timestamp": _now(),
    })
    _save_progress(blueprint_id, progress)
    print(f"Deviation logged for phase {phase_num}: {description}")


def cmd_status(blueprint_id: str) -> None:
    """Show current progress status."""
    progress = _load_progress(blueprint_id)
    if not progress:
        print(f"No progress found for {blueprint_id}", file=sys.stderr)
        sys.exit(1)

    print(f"Blueprint: {progress.get('title', blueprint_id)}")
    print(f"Status: {progress.get('status', 'unknown')}")
    print(f"Started: {progress.get('started_at', '?')}")
    print()

    for pnum, phase in sorted(progress.get("phases", {}).items()):
        status_icon = {"pending": " ", "in_progress": ">", "completed": "x",
                       "blocked": "!"}
        icon = status_icon.get(phase["status"], "?")
        tasks = phase.get("tasks", {})
        done_count = sum(1 for t in tasks.values() if t.get("done"))
        print(f"  [{icon}] Phase {pnum}: {phase['title']} "
              f"({done_count}/{len(tasks)} tasks)")

    devs = progress.get("deviations", [])
    if devs:
        print(f"\nDeviations: {len(devs)}")
        for d in devs:
            print(f"  - Phase {d['phase']}: {d['description']}")


def cmd_report(blueprint_id: str) -> None:
    """Generate a completion report as markdown."""
    progress = _load_progress(blueprint_id)
    if not progress:
        print(f"No progress found for {blueprint_id}", file=sys.stderr)
        sys.exit(1)

    lines = [
        f"# Execution Report: {progress.get('title', blueprint_id)}",
        "",
        f"> **Blueprint ID**: {blueprint_id}",
        f"> **Status**: {progress.get('status', 'unknown')}",
        f"> **Started**: {progress.get('started_at', '?')}",
        f"> **Completed**: {progress.get('completed_at', 'in progress')}",
        "",
        "## Phase Summary",
        "",
        "| Phase | Title | Status | Duration |",
        "|-------|-------|--------|----------|",
    ]

    for pnum, phase in sorted(progress.get("phases", {}).items()):
        started = phase.get("started_at", "")
        completed = phase.get("completed_at", "")
        if started and completed:
            # Simple duration display
            duration = "done"
        elif started:
            duration = "in progress"
        else:
            duration = "-"
        lines.append(
            f"| {pnum} | {phase['title']} | {phase['status']} | {duration} |"
        )

    devs = progress.get("deviations", [])
    if devs:
        lines.extend(["", "## Deviations", ""])
        for d in devs:
            lines.append(
                f"- **Phase {d['phase']}** ({d['timestamp']}): {d['description']}"
            )

    unplanned = progress.get("unplanned_work", [])
    if unplanned:
        lines.extend(["", "## Unplanned Work", ""])
        for u in unplanned:
            lines.append(f"- {u}")

    report = "\n".join(lines) + "\n"

    # Save report
    report_path = BLUEPRINTS_DIR / blueprint_id / "report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)

    print(report)
    print(f"\nReport saved to: {report_path}", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "init": (cmd_init, 1, "<blueprint.md>"),
        "start-phase": (cmd_start_phase, 2, "<blueprint-id> <phase-num>"),
        "complete-phase": (cmd_complete_phase, 2, "<blueprint-id> <phase-num>"),
        "complete-task": (cmd_complete_task, 2, "<blueprint-id> <task-id>"),
        "deviation": (cmd_deviation, 3, "<blueprint-id> <phase-num> <description>"),
        "status": (cmd_status, 1, "<blueprint-id>"),
        "report": (cmd_report, 1, "<blueprint-id>"),
    }

    if cmd not in commands:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(commands)}")
        sys.exit(1)

    func, min_args, usage = commands[cmd]
    if len(args) < min_args:
        print(f"Usage: progress_tracker.py {cmd} {usage}")
        sys.exit(1)

    func(*args[:min_args])


if __name__ == "__main__":
    main()
