# Focal Project Management Guide

Focal's `pm` commands let you manage your entire delivery lifecycle — epics, stories,
iteration planning, and retrospectives — using only GitHub Issues, GitHub Projects,
and markdown files in your repo. No Jira, no Linear, no external tools.

---

## Prerequisites

- `focal board setup` completed (personal board configured)
- `gh` CLI authenticated with `repo` and `project` scopes
- A GitHub Projects v2 board configured in `config.json` (set during `focal board setup`)

---

## Delivery workflow

Focal separates **thinking** from **execution**. The thinking (design, planning) is done
by you or your AI agent. The execution (creating GitHub issues, updating boards, logging
velocity) is done by Focal. Neither step blocks the other — you can write design docs
without Focal, and you can run Focal commands without design docs. But together they form
a complete, traceable delivery system.

```
Step 1  focal pm init owner/repo
        └─ scaffolds docs/focal/, labels, issue templates

Step 2  Write design docs  →  docs/focal/design/D001-feature.md
        └─ human or AI agent — problem, goals, impact, breakdown hint

Step 3  Plan epics & stories
        └─ human or AI agent reads design docs, decides structure + SP

Step 4  focal pm epic-create owner/repo    # repeat per epic
        focal pm story-create owner/repo   # repeat per story

Step 5  focal pm plan owner/repo
        └─ generates docs/focal/iteration-planning.md from local cache

Step 6  focal board sync                   # runs hourly via scheduler
        └─ keeps personal board in sync during delivery

Step 7  focal pm retro owner/repo          # at end of each iteration
        └─ logs velocity + retrospective to docs/focal/retro-log.md

Step 8  focal pm status owner/repo         # any time during an iteration
        └─ live terminal summary of current iteration
```

**Tip:** run `focal cache refresh owner/repo` any time to pull in issues created or
updated directly on GitHub (outside Focal commands).

### Step 3 in detail — planning with an AI agent

Steps 2 and 3 are where Focal's AI-native design pays off. After writing a design doc,
you can hand it to your AI agent with a single prompt:

> *"Read docs/focal/design/D001-my-feature.md and use the breakdown hint to create the
> epics and stories with `focal pm epic-create` and `focal pm story-create`."*

The agent reads the design doc — especially the **Breakdown hint** and **Impact**
sections — and runs the Focal commands to create the backlog. Story point estimates,
epic groupings, and impact-driven stories (e.g. a migration story for a Breaking impact)
all flow from the design doc into GitHub without manual data entry.

This is the intended happy path. Focal ships with [`AGENTS.md`](../AGENTS.md) so any
capable AI agent already knows how to operate it before you say a word.

---

## Quick-start (commands only)

All commands work interactively (prompts) without flags, or fully non-interactively
when all flags are supplied — useful for scripting and AI agents.

```bash
# Interactive — prompts for all inputs
python3 focal.py pm init owner/repo
python3 focal.py pm epic-create owner/repo
python3 focal.py pm story-create owner/repo
python3 focal.py pm plan owner/repo
python3 focal.py pm retro owner/repo
python3 focal.py pm status owner/repo
python3 focal.py cache refresh owner/repo

# Non-interactive — common flags (see each command section for full reference)
python3 focal.py pm epic-create owner/repo --title "Title" --description "..." --sp 8
python3 focal.py pm story-create owner/repo --epic E1 --title "Title" --sp 3
python3 focal.py pm plan owner/repo --weeks 2 --start 2026-05-19 --team "alice:8,bob:6"
python3 focal.py pm retro owner/repo --iteration I1 --goal-met --notes "..."
```

---

## Design docs

Design docs live in `docs/focal/design/` and are the starting point for any non-trivial
feature. They capture the problem, the approach, and crucially — the **Impact** and
**Breakdown hint** sections that Focal and AI agents use to generate the backlog.

### Creating a design doc

Copy the template and fill it in:

```bash
cp templates/design/design-template.md docs/focal/design/D001-my-feature.md
```

File naming: `D{NNN}-short-kebab-title.md` — IDs are assigned sequentially per repo.

### Template sections

| Section | Purpose |
|---------|---------|
| **Abstract** | 2–4 sentence summary — what, why, what problem |
| **Problem** | Specific failure mode or gap, with examples |
| **Goals / Non-goals** | What is in scope and explicitly out of scope |
| **User stories** | "As a [user], I want [action] so that [outcome]" |
| **Design** | Technical approach — components, data flow, key decisions |
| **Impact** | Blast radius table — API, schema, security, other components |
| **Alternatives considered** | What was evaluated and rejected, and why |
| **Open questions** | Unresolved issues with owner and due date |
| **Breakdown hint** | Suggested epic/story structure for AI agents and planners |
| **References** | URLs, related designs, prior art |

### The Impact section

Every design doc must have an Impact table. For each area, state the level and add notes
if non-None:

| Level | Meaning |
|-------|---------|
| **None** | No change to this area |
| **Additive** | New behaviour, fully backwards-compatible |
| **Breaking** | Existing callers or data must change — requires a migration story |
| **Needs review** | Uncertain — flag for a specialist before implementation starts |

An AI agent reading a design doc with `Breaking` impact will automatically add a
migration or compatibility story when creating the backlog via `focal pm story-create`.

### The Breakdown hint section

The breakdown hint is plain-English guidance for turning the design into epics and
stories. Write it as you would brief a colleague:

```markdown
## Breakdown hint

Epic: Board sync engine (~23 SP)
  - Story: Implement polling loop (5 SP)
  - Story: Add state file persistence (3 SP)
  - Story: Push status changes to origin projects (8 SP)
  - Story: Handle stale/closed issues (5 SP)
  - Story: Add structured logging (2 SP)

Epic: Setup wizard (~13 SP)
  - Story: Interactive board URL parser (3 SP)
  - Story: Repo selection (interactive + full scan modes) (5 SP)
  - Story: Status column inspection and status_map generation (5 SP)
```

An AI agent running `focal pm epic-create` and `focal pm story-create` uses this section
as its primary input — it does not need to infer the structure from the rest of the doc.

---

## Commands

### `focal pm init`

Bootstrap a repo with the Focal project management structure. Safe to re-run — existing files are never overwritten.

```bash
python3 focal.py pm init <owner/repo> [--repo-root PATH]
```

**What it creates:**

| Path | Purpose |
|------|---------|
| `.github/ISSUE_TEMPLATE/epic.md` | GitHub issue template for epics |
| `.github/ISSUE_TEMPLATE/story.md` | GitHub issue template for stories |
| `docs/focal/epics.md` | Epic/story tracker with SP rollups |
| `docs/focal/iteration-planning.md` | Capacity, schedule, and risk register |
| `docs/focal/retro-log.md` | Velocity and retrospective history |
| `docs/focal/design/` | Directory for per-feature design records |

**Labels created:** `epic` (purple) · `story` (blue)

**Customise templates:** Edit files in `focal/templates/` before running init.
Your changes will be applied to every repo you initialise.

**Example:**

```
$ python3 focal.py pm init leninmehedy/my-project
  ✔ Label 'epic' ready
  ✔ Label 'story' ready
  ✔ .github/ISSUE_TEMPLATE/epic.md
  ✔ .github/ISSUE_TEMPLATE/story.md
  ✔ docs/focal/epics.md
  ✔ docs/focal/iteration-planning.md
  ✔ docs/focal/retro-log.md
  ✔ docs/focal/design/
```

---

### `focal pm epic-create`

Guided wizard to create a GitHub epic issue and record it in `docs/focal/epics.md`.

```bash
python3 focal.py pm epic-create <owner/repo> [--repo-root PATH]
```

**What it does:**

1. Prompts for epic title, description, and SP estimate
2. Creates a GitHub Issue with the `epic` label, assigned to you
3. Adds the issue to your project board
4. Appends a structured entry to `docs/focal/epics.md` with an auto-incremented ID (E1, E2, …)
5. Updates the local state cache and commits `docs/focal/epics.md`

**Epic format in `docs/focal/epics.md`:**

```markdown
## E3 — Add OAuth support · [#42](https://github.com/.../issues/42) · 21 SP

Allow users to log in with GitHub and Google.

| Story | GitHub | SP |
|---|---|---|
```

**Example:**

```
$ python3 focal.py pm epic-create leninmehedy/my-project
  Title: Add OAuth support
  Description: Allow users to log in with GitHub and Google.
  Estimate (SP): 21
  ✔ Created issue #42 — Epic: Add OAuth support
  ✔ Added to project board
  ✔ docs/focal/epics.md updated (E3)
  ✔ Local state updated
  ✔ Committed
```

---

### `focal pm story-create`

Create a story issue attached to an existing epic.

```bash
python3 focal.py pm story-create <owner/repo> [--repo-root PATH]
```

**What it does:**

1. Lists open epics from local state and prompts you to select one
2. Prompts for story title, description, and SP estimate
3. Creates a GitHub Issue with the `story` label, linked as sub-issue to the epic
4. Adds the issue to the project board with SP set
5. Appends the story row to the epic's table in `docs/focal/epics.md` (auto-numbered 1.1, 1.2, …)
6. Updates the local state cache and commits `docs/focal/epics.md`

**Example:**

```
$ python3 focal.py pm story-create leninmehedy/my-project
  Select epic:
    1  E3 — Add OAuth support (#42) · 21 SP
  Choice: 1
  Story title: Implement GitHub OAuth flow
  Description: Add GitHub OAuth callback endpoint and session handling.
  Estimate (SP): 5
  ✔ Created issue #43 — Implement GitHub OAuth flow
  ✔ Linked as sub-issue to #42
  ✔ Story point set: 5 SP
  ✔ docs/focal/epics.md updated (3.1)
  ✔ Local state updated
  ✔ Committed
```

**Story row added to `docs/focal/epics.md`:**

```markdown
| **3.1** — Implement GitHub OAuth flow | [#43](https://github.com/.../issues/43) | 5 |
```

---

### `focal pm plan`

Generate or update `docs/focal/iteration-planning.md` from the local state cache.

```bash
python3 focal.py pm plan <owner/repo> [--repo-root PATH] [--refresh]
```

**What it does:**

1. Reads all open stories, their SP, assignees, and current status from local cache
2. Prompts for iteration length (weeks) and start date
3. Prompts for team members and capacity (SP/iteration) per person
4. Prompts for PTO/travel dates — reduces capacity for affected iterations automatically
5. Prompts for an iteration goal for each planned iteration (used later in `retro`)
6. Groups stories into iterations by SP capacity (greedy, highest-known-SP first)
7. Identifies risks: stories without estimates, unassigned stories, blocked items
8. Writes structured markdown to `docs/focal/iteration-planning.md`
9. Persists the iteration schedule to local state and commits

Use `--refresh` to re-fetch all story state from GitHub before planning.

**Example:**

```
$ python3 focal.py pm plan leninmehedy/my-project
  Iteration length (weeks) [2]: 2
  Start date [2026-05-18]: 2026-05-18
  GitHub handles (comma-separated): leninmehedy,collaborator
  Capacity for @leninmehedy (SP/iter) [8]: 8
  Capacity for @collaborator (SP/iter) [8]: 6
  Any PTO or travel? (y/N): y
    @leninmehedy away from: 2026-06-27
    @leninmehedy away until: 2026-07-04

  Iteration goals (used in retro — blank to skip)
  I1 goal: Ship auth middleware refactor
  I2 goal: Close E2 OAuth epic

  ✔ docs/focal/iteration-planning.md written
  ✔ Local state updated
  ✔ Committed
  Plan generated — 4 iteration(s)
```

**Tip:** if stories were created or updated outside Focal, run `focal cache refresh` before
`focal pm plan` to ensure the plan reflects current GitHub state.

---

### `focal pm retro`

Close out a completed iteration and append a retrospective record to `docs/focal/retro-log.md`.

```bash
python3 focal.py pm retro <owner/repo> [--repo-root PATH] [--refresh]
```

**What it does:**

1. Lists planned iterations and prompts you to select one
2. Checks GitHub Issues live to split stories into delivered vs carry-over
3. Prompts for a slip reason code per carry-over story
4. Asks whether the iteration goal was met (reads the goal set during `focal pm plan`)
5. Prompts for what went well and what to improve (bulleted lists)
6. Prompts for action items with owner and optional due date
7. Calculates velocity: planned SP, delivered SP, carry-over SP
8. Appends a structured block to `docs/focal/retro-log.md`
9. Updates the cumulative velocity table and commits

Use `--refresh` to re-fetch all story state from GitHub before logging.

**Slip reason codes:**

| Code | Meaning |
|------|---------|
| `SCOPE` | Story was larger than estimated |
| `BLOCKED` | External dependency or blocker |
| `LEAVE` | Engineer on unplanned leave |
| `TRAVEL` | Engineer travelling / at conference |
| `CARRY` | Underestimated — carries forward |
| `REPRIORITY` | Deprioritised by stakeholder |

**Example:**

```
$ python3 focal.py pm retro leninmehedy/my-project
  Select iteration to close:
    1  I1 — 2026-05-18 → 2026-05-31  (14 SP)
  Choice: 1

  Checking GitHub issue status for 3 stories...
  ✔ Delivered: 2 stories · Carry-over: 1 story

  Slip reasons (for carry-over stories)
  #44 Add Google OAuth flow [5 SP]: SCOPE
    Optional note: session handling took longer than expected

  Iteration goal: Ship auth middleware refactor
  Goal met? [Y/n]: Y

  What went well? (one per line, blank to finish)
    • Pairing sessions kept blockers short
    •

  What to improve? (one per line, blank to finish)
    • SP estimates for auth work were too optimistic
    •

  Action items (blank handle to finish)
    Owner handle: leninmehedy
    @leninmehedy: action: Re-estimate carry-over stories before I2
    Due date: 2026-06-02
    Owner handle:

  Free-form notes: Good iteration overall despite scope slip on #44.

  ✔ docs/focal/retro-log.md updated
  ✔ Committed
  Retro logged — I1
  Planned: 14 SP · Delivered: 9 SP · Carry-over: 5 SP
```

**Record appended to `docs/focal/retro-log.md`:**

```markdown
## I1 — May 18, 2026 – May 31, 2026

### Goal

> Ship auth middleware refactor

**Met:** ✅ Yes

### Planned
- @leninmehedy: [#43](https://github.com/.../issues/43) GitHub OAuth flow (5 SP)
- @leninmehedy: [#44](https://github.com/.../issues/44) Google OAuth flow (5 SP)
- @leninmehedy: [#45](https://github.com/.../issues/45) Auth middleware (4 SP)

### Delivered
- @leninmehedy: [#43](https://github.com/.../issues/43) GitHub OAuth flow (5 SP)
- @leninmehedy: [#45](https://github.com/.../issues/45) Auth middleware (4 SP)

### Velocity

- Planned: **14 SP** · Delivered: **9 SP** · Carry-over: **5 SP**

### Slip Reasons

- [#44](https://github.com/.../issues/44) Google OAuth flow — **SCOPE** — session handling took longer than expected

### What went well

- Pairing sessions kept blockers short

### What to improve

- SP estimates for auth work were too optimistic

### Action items

- [ ] @leninmehedy: Re-estimate carry-over stories before I2 (by 2026-06-02)

### Notes

Good iteration overall despite scope slip on #44.

---
```

---

### `focal pm status`

Print a live terminal summary of the current iteration.

```bash
python3 focal.py pm status <owner/repo> [--repo-root PATH] [--refresh]
```

Reads story state from the local cache. Use `--refresh` to pull the latest status
from GitHub before displaying (adds a "Last synced" timestamp to the output).

**Example output:**

```
  ◎  Focal — status (leninmehedy/my-project)

Focal Board — I1 (May 18 – May 31)
────────────────────────────────────────────────────────
  Delivered       ████████░░░░░░░░░░░░░░░░  9 / 14 SP (64%)
  In progress     2 stories · 5 SP
  Blocked         0 stories · 0 SP
  Not started     1 story   · 0 SP

  Days remaining:  6
  Projected:       13 SP (93%)
```

Blocked stories are listed in detail below the summary if any are present.

---

### `focal cache refresh`

Re-fetch all epic, story, and project-board state from GitHub and update the local cache.

```bash
python3 focal.py cache refresh <owner/repo> [--repo-root PATH]
```

**When to run:**

- Issues were created or updated directly on GitHub (outside Focal commands)
- Project board statuses were changed manually
- Before `focal pm plan` or `focal pm retro` when you want guaranteed fresh data
  (or use the `--refresh` flag on those commands directly)

The local cache at `docs/focal/.cache/focal-state.json` is the source of truth for
`plan`, `retro`, and `status`. GitHub is always the authority — the cache is just a
read-through for speed.

**Example:**

```
$ python3 focal.py cache refresh leninmehedy/my-project
  ✔ Synced 3 epics, 14 stories
  ✔ Last synced: 2026-05-18T09:42:11+00:00
```

---

## File structure after `focal pm init`

```
your-repo/
  .github/
    ISSUE_TEMPLATE/
      epic.md                    ← GitHub template for epic issues
      story.md                   ← GitHub template for story issues
  docs/
    focal/
      epics.md                   ← epic/story tracker, updated by epic-create/story-create
      iteration-planning.md      ← capacity + schedule, updated by focal pm plan
      retro-log.md               ← velocity + retrospective history, updated by focal pm retro
      design/                    ← per-feature design records (manual)
      .cache/
        focal-state.json         ← local state cache (do not edit manually)
```

---

## Customising templates

Templates live in `focal/templates/`. Edit them before running `focal pm init` to match
your team's conventions — column names, status codes, ceremony schedules, etc.

```
focal/
  templates/
    epics.md
    iteration-planning.md
    retro-log.md
    ISSUE_TEMPLATE/
      epic.md
      story.md
    design/
      design-template.md
```

Changes to these files take effect the next time you run `focal pm init` on a new repo.
Existing repos are not affected (files are never overwritten).
