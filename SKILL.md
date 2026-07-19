---
name: executor
description: "executor, blueprint, execute, run, plan, start, executing, 按照藍圖執行, 開始跑計劃, 照計劃做, 執行 blueprint"
version: 0.2.0
tools: Read, Bash, Edit, Write, Glob, Grep, sandbox_execute
argument-hint: "<blueprint-file-path or blueprint-id>"
disable-model-invocation: true
---

# Executor — Faithful Plan Execution

Read a blueprint file and execute it phase by phase with discipline:
track progress, verify each phase, log deviations, and produce a completion report.

## Agent Delegation

Delegate phase execution to `worker` agent. Use `reviewer` for verification between phases.

## Core Principle

**Follow the plan. Don't improvise.**

The blueprint was approved for a reason. If reality diverges from the plan,
LOG the deviation and DECIDE whether to continue or stop — don't silently
drift. The user approved a specific scope; honor it.

## Workflow

### Step 1: Load the Blueprint

Locate and read the blueprint file.

**Preferred (Sandbox)**:
```python
# sandbox_execute
import sys
sys.path.insert(0, "/Users/joneshong/.claude/skills/executor/scripts")
import parse_blueprint
data = parse_blueprint.parse("/Users/joneshong/.claude/data/blueprints/{file}.md")
output(data)
```

**Fallback (Bash)**:
```bash
# By path
~/.local/bin/python3 ~/.claude/skills/executor/scripts/parse_blueprint.py ~/.claude/data/blueprints/{file}.md

# List available blueprints
ls -lt ~/.claude/data/blueprints/*.md | head -10
```

The parser extracts structured data: phases, tasks, dependencies, verification commands.

If no blueprint exists, suggest running `/blueprint` first.

### Step 2: Validate Prerequisites

Before starting execution:

1. **Check blueprint status** — must be `approved` or `in-progress`
2. **Verify all source files exist** — every file in the affected files table
   that has Op=MOD must exist. Op=NEW files must NOT exist yet.
3. **Check dependencies** — external tools, services, packages available
4. **Load progress** — if resuming, read `~/.claude/data/blueprints/{id}/progress.json`

If validation fails, report the issue and stop.

### Step 3: Create Progress Tracker

```bash
~/.local/bin/python3 ~/.claude/skills/executor/scripts/progress_tracker.py init {blueprint-path}
```

This creates `~/.claude/data/blueprints/{id}/progress.json` tracking:
- Phase status (pending / in_progress / completed / blocked)
- Task completion checkboxes
- Deviation log
- Timestamps

Also create a TaskList using the built-in task tracking (TaskCreate) for
visibility in the session.

### Step 4: Execute Phase by Phase

For each phase, in dependency order:

#### 4a. Check Dependencies
Verify all prerequisite phases are completed. If a dependency is blocked,
skip to the next eligible phase or stop.

#### 4b. Mark In-Progress
```bash
~/.local/bin/python3 ~/.claude/skills/executor/scripts/progress_tracker.py start-phase {id} {phase-num}
```

#### 4c. Execute Tasks
Work through the task list sequentially. For each task:

1. Read the task description from the blueprint
2. Execute the required changes (edit files, run commands)
3. Mark the task complete in progress tracker

**Deviation protocol**: If a task cannot be completed as described:

| Situation | Action |
|-----------|--------|
| Minor adjustment (e.g., line number shifted) | Log and continue |
| File doesn't exist or has different structure | Log, adapt, continue |
| New file discovered that needs changes | Log as unplanned work, add to cross-cut |
| Fundamental approach doesn't work | STOP, report to user |

Log deviations:
```bash
~/.local/bin/python3 ~/.claude/skills/executor/scripts/progress_tracker.py deviation {id} {phase} "description"
```

#### 4d. Verify Phase
Run the verification command from the blueprint's done criteria.
Apply `verification-before-completion` discipline:
- Run the EXACT command specified
- Check exit code AND output
- Only mark complete if verification passes

```bash
~/.local/bin/python3 ~/.claude/skills/executor/scripts/progress_tracker.py complete-phase {id} {phase-num}
```

If verification fails, log the failure and attempt to fix. If fix fails, mark
the phase as blocked and report.

### Step 5: Cross-cutting Sweep

After all phases complete, address cross-cutting concerns from the blueprint:

1. Read the cross-cutting concerns list
2. For each concern, run the suggested verification (usually a Grep sweep)
3. Fix any remaining issues
4. Mark each concern as resolved

### Step 6: Final Verification

Run every item in the blueprint's Final Verification Checklist:

- Execute test suites
- Run linters
- Verify no residual references (Grep sweep)
- Check service health (if applicable)

### Step 7: Completion Report

```bash
~/.local/bin/python3 ~/.claude/skills/executor/scripts/progress_tracker.py report {id}
```

Report includes:
- Blueprint ID and title
- Execution timeline (start → end per phase)
- All deviations logged
- Unplanned work discovered
- Verification results
- Final status: COMPLETED / PARTIAL / BLOCKED

Update blueprint status line to `completed`.

Save report to: `~/.claude/data/blueprints/{id}/report.md`

## Resuming Interrupted Execution

If a session ends mid-execution (context limit, crash, user pause):

1. Read `progress.json` to find last completed phase
2. Read any logged deviations
3. Resume from the next pending phase
4. The progress tracker preserves full state

This integrates with Document & Clear: save progress file path to
`PROGRESS.md`, clear context, then resume by reading the progress file.

## Autonomous vs Interactive Mode

**Autonomous** (default for straightforward blueprints):
- Execute all phases without pausing for user input
- Report deviations at the end
- Stop only on BLOCK-level issues

**Interactive** (when blueprint involves risky or irreversible changes):
- Pause after each phase for user review
- Present deviation log for approval before continuing
- Recommended for: database migrations, infrastructure changes, public API changes

Determine mode from blueprint risk assessment. If any risk has Impact=H,
default to interactive.

## Integration with Other Skills

| Skill | Relationship |
|-------|-------------|
| **blueprint** | Executor consumes blueprint output |
| **verification-before-completion** | Verification discipline applied per phase |
| **team-tasks** | For multi-agent execution, create team-tasks from blueprint phases |
| **maestro** | For dispatching phases to different CLIs based on task type |

## Sandbox Optimization

This skill is **sandbox-optimized**. Batch operations run inside `sandbox_execute`:

- **Blueprint parsing**: Import `scripts/parse_blueprint.py` in sandbox to extract all phases, tasks, and dependencies in one call
- **Progress tracker init**: Import `scripts/progress_tracker.py` in sandbox to initialize and update `progress.json` without separate subprocess overhead

Principle: **Deterministic batch work → sandbox; reasoning/presentation → LLM.**

## Additional Resources

### Reference Files
- **`references/deviation-protocol.md`** — Detailed deviation classification and response guide
