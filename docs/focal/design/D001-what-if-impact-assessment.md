---
id: D001
title: What-if impact assessment for iteration planning
author: @leninmehedy
status: Done
epic: 69
created: 2026-05-19
updated: 2026-05-20
relates-to:
---

# D001 — What-if impact assessment for iteration planning

## Abstract

`focal pm what-if` is a dry-run simulation command that answers the question
"what happens to my iteration plan if X occurs?" — where X is an unplanned
absence, an urgent work injection, or a scope change. It reads the current
iteration plan and backlog, applies a hypothetical scenario, and produces a
before/after impact report without touching any files or GitHub state.

## Problem

An engineer managing multiple repos via Focal has iteration plans that assume
a stable capacity. Real delivery constantly breaks that assumption:

- **Unplanned leave** — "I'm sick next week. What slips?"
- **Work injection** — "An urgent P1 bug just came in, taking 5 days. Which
  stories get pushed to next iteration?"
- **Team change** — "Bob is on PTO for two weeks mid-sprint. How does that
  change our projected delivery?"
- **Scope increase** — "This story turned out to be 13 SP, not 5. What's the
  ripple effect?"

Today the engineer must manually re-read the iteration plan, recalculate
capacity, and mentally re-simulate story assignment — a slow, error-prone
process that usually gets skipped. The real impact is only discovered at retro
time, by which point it's too late to act.

## Goals

- ✅ Simulate capacity reduction from unplanned leave for any team member
- ✅ Simulate injection of a new urgent task (any SP value) into the current
  iteration
- ✅ Simulate a story re-estimate (SP change for an existing story)
- ✅ Show a before/after diff: which stories slip, which iterations shift,
  new projected delivery dates
- ✅ Operate purely as a dry-run — no files written, no GitHub calls, no state
  changes unless `--apply` is passed
- ✅ Work across all repos registered via `focal pm init` in one pass, or
  target a single repo
- ✅ Support non-interactive invocation so AI agents can run it and report
  results in plain language

## Non-goals

- ❌ Real-time GitHub integration — does not fetch live issue state during the
  simulation (use `focal cache refresh` first if you want fresh data)
- ❌ Multi-person conflict modelling (e.g. "what if two people are both out") —
  each `--pto` flag is additive; the combined effect is computed correctly, but
  the command does not reason about team interdependencies
- ❌ Automatic re-planning with GitHub mutations — `--apply` only rewrites the
  local `iteration-planning.md`, it does not close/move GitHub issues
- ❌ Probabilistic risk modelling — the simulation is deterministic given the
  inputs; uncertainty estimation is out of scope

## User stories

- As an **engineer**, I want to run `focal pm what-if --pto "me:next-week"` and
  immediately see which stories slip and by how many iterations, so I can
  decide whether to delegate or descope before taking leave.

- As a **tech lead**, I want to simulate injecting a P1 bug (`--inject "Fix
  prod outage:8SP"`) and see the ripple effect across all my managed repos'
  iteration plans, so I can set stakeholder expectations before committing.

- As an **engineer**, I want to re-estimate a story that turned out to be
  bigger (`--reestimate S2.3:13`) and see how that changes the current
  iteration's projected delivery date.

- As a **manager**, I want to run `focal pm what-if --apply` to write the
  updated iteration plan after confirming the simulated scenario is accurate,
  without re-running `focal pm plan` from scratch.

## Design

### Overview

```
focal pm what-if leninmehedy/focal \
  --pto "alice:2026-06-02:2026-06-06" \
  --inject "Urgent prod fix:8" \
  --reestimate "1.3:13"
```

The command:
1. Loads current iteration plan from `docs/focal/iteration-planning.md`
2. Loads current backlog from the local state cache
3. Applies the scenario (PTO reduction, injection, re-estimate) to a
   **copy** of the plan in memory
4. Re-runs the greedy SP assignment algorithm on the modified capacity/backlog
5. Produces a structured impact report comparing original vs simulated plan
6. Optionally writes the updated `iteration-planning.md` with `--apply`

### Components

| Component | Role |
|---|---|
| `focal/pm/whatif_cmd.py` | Main command logic — orchestrates load, simulate, report |
| `focal/pm/plan_cmd.py` | Reuses `_greedy_assign()` and capacity helpers (extract to shared) |
| `focal/pm/iteration_parser.py` | New: parses `iteration-planning.md` into structured data |
| `focal/_cli.py` | New `focal pm what-if` command registration |

### Data / schema

The simulation works entirely on in-memory data derived from existing files —
no new on-disk format is needed.

**Scenario input** (CLI flags → internal dict):
```python
{
  "pto": [{"handle": "alice", "from": "2026-06-02", "to": "2026-06-06"}],
  "inject": [{"title": "Urgent prod fix", "sp": 8}],
  "reestimate": [{"story_id": "1.3", "new_sp": 13}],
}
```

**Impact report** (in-memory, rendered to terminal):
```python
{
  "iterations": [
    {
      "label": "I2",
      "original": {"stories": [...], "total_sp": 14, "end": "2026-06-13"},
      "simulated": {"stories": [...], "total_sp": 10, "end": "2026-06-13"},
      "slipped": ["story_1.3", "story_1.4"],   # moved to next iter
      "injected": ["Urgent prod fix"],
    }
  ],
  "summary": {
    "total_slipped_sp": 8,
    "iterations_extended": 1,
    "projected_completion_shift_days": 14,
  }
}
```

### Sequence / flow

```
1. Parse CLI flags → build scenario dict
2. Load iteration plan:
     iteration_parser.load(repo_root / "docs/focal/iteration-planning.md")
     → list of iterations with story IDs, dates, capacity per person
3. Load backlog from state cache:
     pm_state.load(repo_root) → all_stories with current SP
4. Apply scenario to a deep copy of plan + backlog:
     a. PTO: subtract leave days from affected person's capacity in each
        overlapping iteration; recompute iteration SP cap
     b. Inject: prepend injected story (high priority) to the unassigned
        backlog for the current iteration
     c. Re-estimate: update SP for matching story_id in backlog copy
5. Re-run greedy assignment on modified data (same algorithm as focal pm plan)
6. Diff original vs simulated:
     - Stories that moved to a later iteration → "slipped"
     - Iterations whose end date shifts → "extended"
     - New projected completion date for each epic
7. Render impact report to terminal (Rich panels, colour-coded)
8. If --apply: write updated iteration-planning.md (same renderer as plan_cmd)
```

### Key decisions

| Decision | Rationale |
|----------|-----------|
| Dry-run by default, `--apply` opt-in | A what-if is exploratory; accidental plan overwrite would be destructive |
| Reuse greedy assignment from `plan_cmd` | Ensures simulation uses identical logic to the original plan — no divergence |
| Parse `iteration-planning.md` → structured data | Avoids requiring a separate "plan state" file; the markdown is the source of truth |
| No GitHub API calls during simulation | Speed and offline use; caller is responsible for cache freshness |
| `--pto` accepts date range or named shorthand | `next-week`, `this-week` resolved to ISO dates at parse time for convenience |

## Impact

| Area | Impact | Notes |
|------|--------|-------|
| Public API / interfaces | Additive | New `focal pm what-if` command; no existing commands changed |
| Data / schema migration | None | No new files; reads existing `iteration-planning.md` and cache |
| Existing functionality | None | `plan_cmd.py` refactored to extract shared helpers |
| Performance | None | All in-memory; no new GitHub API calls |
| Security | None | |
| Dependencies | None | No new packages |
| Other components / services | None | |

## Alternatives considered

| Alternative | Why rejected |
|-------------|-------------|
| Extend `focal pm plan` with `--simulate` flag | Conflates planning (writes files) with simulation (read-only); separate command is clearer |
| Store plan as JSON alongside the markdown | Adds a second source of truth; markdown is already the plan record — parse it |
| Interactive wizard (prompt for each scenario param) | Non-interactive flags are required for AI agent use; prompts can be layered on top later |

## Open questions

- [ ] **Q1** — How to handle stories that have no SP estimate in the simulation?
  Options: treat as 0 (ignore), treat as a configurable default (e.g. 3 SP),
  or surface as a warning. *(owner: @leninmehedy, due: 2026-05-30)*

- [ ] **Q2** — Should `--apply` also create a GitHub comment on affected epic
  issues summarising the impact? Useful for stakeholder visibility but adds
  GitHub API calls to an otherwise offline command.
  *(owner: @leninmehedy, due: 2026-05-30)*

## Breakdown hint

Epic: What-if impact assessment (focal pm what-if) (~34 SP)
  - Story: Extract shared plan helpers from plan_cmd.py (greedy assign, capacity calc) (3 SP)
  - Story: Implement iteration_parser.py — parse iteration-planning.md into structured data (5 SP)
  - Story: Implement scenario application — PTO capacity reduction (5 SP)
  - Story: Implement scenario application — work injection (new story into current iter) (3 SP)
  - Story: Implement scenario application — story re-estimate (SP update + ripple) (3 SP)
  - Story: Implement diff engine — original vs simulated, identify slipped stories (5 SP)
  - Story: Implement impact report renderer (Rich terminal output, before/after) (5 SP)
  - Story: Wire up focal pm what-if CLI command with all flags (3 SP)
  - Story: Add --apply flag to write updated iteration-planning.md (3 SP)

## References

- `docs/focal/iteration-planning.md` — the file this command reads and optionally writes
- `focal/pm/plan_cmd.py` — greedy SP assignment algorithm to be reused
- `focal/pm/pm_state.py` — state cache API
- [Focal PM Guide](../pm-guide.md) — overall PM workflow context
