---
id: D004
title: "focal pm adopt-plan: bootstrap a project from a plan doc (plan.md)"
author: @leninmehedy
status: Active
epic: 147
created: 2026-06-08
updated: 2026-06-08
relates-to: D002
---

# D004 — focal pm adopt-plan: bootstrap a project from a plan doc (plan.md)

## Abstract

Two files, two owners:

- **`docs/focal/plan.md`** — human/agent-authored. Contains the planning narrative:
  release ladder, dependency graph, rationale, epic/story tables with SP estimates.
  Focal **never writes** to this file. Git history of plan.md = the evolution of
  thinking over time.

- **`docs/focal/epics.md`** — focal-owned. Fully re-rendered from `focal-state.json`
  on every mutating command (`adopt-plan`, `epic-create`, `story-create`, `cache
  refresh`). Humans never edit it — it is always a clean, current snapshot.

`focal pm adopt-plan owner/repo` reads `plan.md`, creates GitHub issues for every
epic and story not yet tracked, updates `focal-state.json`, and re-renders `epics.md`.
After bootstrap, `epic-create` and `story-create` continue re-rendering `epics.md`
on every call — no surgical writing, no append logic, no format fragility.

---

## Problem

Developers already write structured plans before touching GitHub. These plans
exist as markdown files and contain more design context than a GitHub issue —
release ladder, dependency graph, rationale per epic. The current focal workflow
discards this artifact: `focal pm init` drops a near-empty scaffold, and there is
no path from "I have a plan doc" to "focal is managing this project."

Additionally, the current `epic-create` and `story-create` commands append to
`epics.md` using regex-based line insertion. This is fragile and produces
inconsistent formatting over time. Re-rendering from cache is simpler, always
correct, and idempotent.

---

## Design

### Two files, clear ownership

```
docs/focal/plan.md      ← human/agent writes this; focal never touches it
docs/focal/epics.md     ← focal re-renders this from focal-state.json
```

`plan.md` is the planning artifact. Its git history shows how thinking evolved.
`epics.md` is the current snapshot. Its git history shows how issues were created
and resolved.

### Re-render instead of append

All mutating PM commands call `render_epics_md(repo_root, state)` after updating
`focal-state.json`. This replaces the current append logic in `epic_cmd.py` and
`story_cmd.py`. The renderer produces a deterministic output from state — no
parsing of the existing file, no surgical substitution.

### adopt-plan flow

```
1. parse_plan_doc("docs/focal/plan.md")
   → ParsedPlanDoc (epics + stories, SP, issue numbers where already present)

2. Dry-run by default: print table of what would be created

3. With --apply:
   a. For each epic with no issue_number:
        focal pm epic-create (via state, not by calling the CLI again)
        → GitHub issue created, focal-state.json updated
   b. For each story with no issue_number:
        GitHub issue created, sub-issue linked to parent epic
        focal-state.json updated
   c. render_epics_md(repo_root, state)
   d. git add docs/focal/epics.md && git commit

4. If no focal pm init yet: run init_cmd.run() first (labels, templates, E0)
```

Idempotent: re-running `adopt-plan --apply` on an already-adopted project skips
issues that already exist in state and is a no-op if nothing is new.

---

## `plan.md` format (human-authored)

`focal pm init` drops this template. Focal reads the epic headings and story
table rows. Everything else is human-authored prose that focal never touches.

```markdown
# Plan

Repository: `owner/repo`

---

## Release ladder

| Epic | Version | Status | Gate |
|---|---|---|---|
| E1 — General Maintenance | ongoing | 🔄 Open | — |
| E2 — Example epic | v0.1 | 📋 Planned | — |

## Dependency graph

```
E1 — General Maintenance (permanent, parallel to all)
E2 — Example epic
```

---

## E1 — General Maintenance · ~ongoing

Catch-all for bugs and unplanned work. Always open.

| Story | SP | Notes |
|---|---|---|
| **1.1** — First story title | 3 | |

---

## E2 — Example epic · ~8 SP

Prose description of the epic — rationale, context, constraints.

| Story | SP | Notes |
|---|---|---|
| **2.1** — First story | 5 | |
| **2.2** — Second story | 3 | |
```

Focal reads:
- `## EN — Title · ~N SP` (or `~ongoing`) — epic headings
- `| **N.M** — Title | N |` — story table rows (SP is the second column)

Focal never reads or writes:
- Release ladder table
- Dependency graph block
- Prose paragraphs under epic headings
- Notes column

---

## `epics.md` format (focal-rendered)

Always generated from `focal-state.json`. Humans never edit this file.

```markdown
<!-- focal-managed: do not edit manually — re-rendered from focal-state.json -->
# Epics & Stories

_Last updated: 2026-06-08 by focal_

---

## E1 — General Maintenance · [#141](url) · ongoing

| Story | GitHub | SP | Status |
|---|---|---|---|
| **1.1** — First story title | [#142](url) | 3 | 🔄 Open |

---

## E2 — Example epic · [#143](url) · 8 SP

| Story | GitHub | SP | Status |
|---|---|---|---|
| **2.1** — First story | [#144](url) | 5 | 📋 Todo |
| **2.2** — Second story | [#145](url) | 3 | 📋 Todo |
```

---

## Parser design — `focal/pm/plan_doc_parser.py`

```python
@dataclass
class ParsedStory:
    local_id: str          # "2.1"
    title: str
    sp: int | None         # None for "ongoing"
    notes: str
    issue_number: int | None  # None if not yet created

@dataclass
class ParsedEpic:
    local_id: str          # "E2"
    title: str
    sp: int | None         # None for "ongoing"
    issue_number: int | None
    stories: list[ParsedStory]

@dataclass
class ParsedPlanDoc:
    repo: str | None       # from "Repository: `owner/repo`"
    epics: list[ParsedEpic]
```

### Regexes

```python
# Matches: ## E2 — Title · ~8 SP   or   ## E1 — General Maintenance · ~ongoing
EPIC_RE = re.compile(
    r"^## (E\w+) — (.+?) · ~(\d+|ongoing) SP?",
    re.MULTILINE,
)

# Matches: | **2.1** — Title | 5 | notes |
STORY_RE = re.compile(
    r"^\| \*\*(\d+\.\w+)\*\* — (.+?) \| (\d+) \|",
    re.MULTILINE,
)
```

---

## Renderer design — `focal/pm/epics_renderer.py`

```python
def render_epics_md(repo_root: Path, state: dict) -> None:
    """Re-render docs/focal/epics.md from focal-state.json."""
```

- Reads `focal-state.json` — iterates epics in ID order, stories in creation order
- Writes `docs/focal/epics.md` atomically (temp file + rename)
- Called by: `adopt_plan_cmd`, `epic_cmd`, `story_cmd`, `cache refresh`
- Replaces the current append logic in `epic_cmd.py` and `story_cmd.py`

---

## Story order

| Story | Issue | SP | What |
|---|---|---|---|
| 2.1 | #148 | 2 | Define canonical `plan.md` format + update `focal pm init` template |
| 2.2 | #149 | 3 | Implement `plan_doc_parser.py` |
| 2.3 | #150 | 3 | Implement `epics_renderer.py` + migrate `epic_cmd` / `story_cmd` to re-render |
| 2.4 | #151 | 5 | Implement `adopt_plan_cmd.py` |
| 2.5 | #152 | 3 | Wire `focal pm adopt-plan` CLI + update `focal pm init` next-steps |
| 2.6 | #153 | 2 | Update `AGENTS.md`, `docs/user-guide.md`, `docs/testing-guide.md` (AP1–AP8) |

---

## Acceptance criteria

- [ ] `focal pm adopt-plan owner/repo` dry-runs by default — prints what would be created
- [ ] `--apply` executes: creates issues, updates state, re-renders `epics.md`
- [ ] Idempotent: re-running `--apply` on an already-adopted project is a no-op
- [ ] `plan.md` is never written by focal under any code path
- [ ] `epics.md` carries a `<!-- focal-managed -->` header warning humans not to edit it
- [ ] `epic-create` and `story-create` re-render `epics.md` from state (no append logic)
- [ ] `focal pm init` drops the `plan.md` template (release ladder + dependency graph sections)
- [ ] `focal pm init` next-steps mention `adopt-plan` as the recommended first step
- [ ] `AGENTS.md` updated with the `plan.md → adopt-plan → board-sync` loop
- [ ] `docs/testing-guide.md` updated with AP1–AP8 test cases
