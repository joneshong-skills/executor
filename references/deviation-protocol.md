# Deviation Protocol

When reality diverges from the blueprint during execution, classify the
deviation and respond accordingly.

## Deviation Classification

### Level 1: Cosmetic (Log & Continue)

No impact on approach or outcome. Just record it.

Examples:
- Line numbers shifted due to upstream changes
- Variable/function was renamed but does the same thing
- File path moved within same directory
- Minor formatting differences

Action: Log the deviation, adjust, continue.

### Level 2: Adaptive (Log, Adapt, Continue)

The task is still achievable but needs a different approach.

Examples:
- File structure differs from blueprint (extra nesting, different module)
- API signature has additional required parameters
- Dependency version changed, slightly different usage
- A test file needs creation that wasn't in the blueprint

Action: Log the deviation with the adaptation made, continue.

### Level 3: Scope Expansion (Log, Flag, Continue with Caution)

New work discovered that wasn't in the blueprint.

Examples:
- Additional consumers found that need updating
- A new config file needs modification
- Test coverage gap discovered
- Related feature needs adjustment

Action: Log as unplanned work, add to cross-cutting concerns,
continue but flag for review.

### Level 4: Blocking (STOP, Report)

The fundamental approach doesn't work. Continuing would waste effort.

Examples:
- Core assumption in the architecture is wrong
- Required API doesn't exist or behaves differently
- Circular dependency discovered
- Performance requirements impossible with chosen approach

Action: STOP execution, report to user with:
1. What was attempted
2. Why it failed
3. What the blueprint assumed vs reality
4. Suggested alternatives

## Deviation Log Format

```json
{
  "phase": "2",
  "level": 2,
  "description": "session_store.py uses Redis instead of dict cache as blueprint assumed",
  "adaptation": "Modified approach to use Redis HSET instead of in-memory dict",
  "timestamp": "2026-02-15T10:30:00Z"
}
```

## Decision Heuristic

```
Can I complete the task as described?
  ├── Yes, just minor differences → Level 1
  ├── Yes, but need different approach → Level 2
  ├── Yes, but more work than planned → Level 3
  └── No, approach is fundamentally wrong → Level 4
```
