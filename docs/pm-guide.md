# Focal Project Management Guide

Focal's `pm` commands let you manage your entire delivery lifecycle — epics, stories,
iteration planning, and retrospectives — using only GitHub Issues, GitHub Projects,
and markdown files in your repo. No Jira, no Linear, no external tools.

---

## Prerequisites

- `focal setup` completed (personal board configured)
- `gh` CLI authenticated with `repo` and `project` scopes
- A GitHub Projects v2 board on the target repo

---

## Quick-start workflow

```
# 1. Bootstrap a repo
python3 focal.py pm init owner/repo

# 2. Create an epic
python3 focal.py pm epic create --repo owner/repo

# 3. Add stories to the epic
python3 focal.py pm story create --repo owner/repo

# 4. Generate the iteration plan
python3 focal.py pm plan --repo owner/repo

# 5. Close out an iteration
python3 focal.py pm retro --repo owner/repo

# 6. Check progress any time
python3 focal.py pm status --repo owner/repo
```

---

## Commands

### `focal pm init`

Bootstrap a repo with the Focal project management structure. Safe to re-run — existing files are never overwritten.

```
python3 focal.py pm init <owner/repo> [--repo-root PATH]
```

**What it creates:**

| Path | Purpose |
|------|---------|
| `.github/ISSUE_TEMPLATE/epic.md` | GitHub issue template for epics |
| `.github/ISSUE_TEMPLATE/story.md` | GitHub issue template for stories |
| `docs/focal/epics.md` | Epic/story tracker with SP rollups |
| `docs/focal/iteration-planning.md` | Capacity, schedule, and risk register |
| `docs/focal/retro-log.md` | Velocity history per iteration |
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

### `focal pm epic create`

Guided wizard to create a GitHub epic issue and record it in `docs/focal/epics.md`.

```
python3 focal.py pm epic create --repo <owner/repo> [--repo-root PATH]
```

**What it does:**

1. Prompts for epic title, description, and SP estimate
2. Creates a GitHub Issue with the `epic` label, assigned to you
3. Adds the issue to your project board
4. Appends a structured entry to `docs/focal/epics.md` with an auto-incremented ID (E1, E2, …)
5. Commits `docs/focal/epics.md`

**Epic format in `docs/focal/epics.md`:**

```markdown
## E3 — Add OAuth support · #42 · 21 SP

Allow users to log in with GitHub and Google.

| Story | GitHub | SP |
|---|---|---|
```

**Example:**

```
$ python3 focal.py pm epic create --repo leninmehedy/my-project
  Title: Add OAuth support
  Description: Allow users to log in with GitHub and Google.
  Estimate (SP): 21
  ✔ Created issue #42 — Epic: Add OAuth support
  ✔ Added to project board
  ✔ docs/focal/epics.md updated (E3)
  ✔ Committed
```

---

### `focal pm story create`

Create a story issue attached to an existing epic.

```
python3 focal.py pm story create --repo <owner/repo> [--repo-root PATH]
```

**What it does:**

1. Lists open epics and prompts you to select one
2. Prompts for story title, description, and SP estimate
3. Creates a GitHub Issue with the `story` label, linked as sub-issue to the epic
4. Adds the issue to the project board with SP set
5. Appends the story row to the epic's table in `docs/focal/epics.md` (auto-numbered 1.1, 1.2, …)
6. Commits `docs/focal/epics.md`

**Example:**

```
$ python3 focal.py pm story create --repo leninmehedy/my-project
  Select epic:
    1. E3 — Add OAuth support (#42) · 21 SP
  Choice: 1
  Title: Implement GitHub OAuth flow
  Description: Add GitHub OAuth callback endpoint and session handling.
  Estimate (SP): 5
  ✔ Created issue #43 — Implement GitHub OAuth flow
  ✔ Linked as sub-issue to #42
  ✔ Story point set: 5 SP
  ✔ docs/focal/epics.md updated (3.1)
  ✔ Committed
```

**Story row added to `docs/focal/epics.md`:**

```markdown
| **3.1** — Implement GitHub OAuth flow | [#43](https://github.com/.../issues/43) | 5 |
```

---

### `focal pm plan`

Generate or update `docs/focal/iteration-planning.md` from current GitHub Issues state.

```
python3 focal.py pm plan --repo <owner/repo> [--repo-root PATH] [--iteration N]
```

**What it does:**

1. Reads all open stories, their SP, assignees, and current status
2. Prompts for iteration length, start date, team members, and capacity per person
3. Prompts for PTO/travel dates (reduces capacity for affected iterations)
4. Groups stories into iterations by SP capacity
5. Identifies risks: stories with no estimate, unassigned epics, blocked items
6. Writes structured markdown to `docs/focal/iteration-planning.md`

**Use `--iteration N`** to plan a specific iteration without regenerating the full document.

**Example:**

```
$ python3 focal.py pm plan --repo leninmehedy/my-project
  Iteration length (weeks) [2]: 2
  Start date [2026-05-18]: 2026-05-18
  Team members (comma-separated GitHub handles): leninmehedy,collaborator
  Capacity for @leninmehedy (SP/iter) [8]: 8
  Capacity for @collaborator (SP/iter) [8]: 6
  Any PTO/travel? (y/N): y
    @leninmehedy away Jun 27–Jul 4 (affects I4)
  ✔ 3 epics · 14 stories · 62 SP total scope
  ✔ Projected delivery: I6 (Aug 9, 2026)
  ✔ docs/focal/iteration-planning.md updated
```

---

### `focal pm retro`

Close out a completed iteration and update `docs/focal/retro-log.md`.

```
python3 focal.py pm retro --repo <owner/repo> [--repo-root PATH] [--iteration N]
```

**What it does:**

1. Reads planned stories for the iteration from `docs/focal/iteration-planning.md`
2. Checks GitHub Issues for which are closed (delivered) vs still open (carry-over)
3. Prompts for a slip reason per carry-over story
4. Calculates velocity: planned SP, delivered SP, carry-over SP
5. Appends a structured iteration record to `docs/focal/retro-log.md`
6. Updates the cumulative velocity table
7. Commits `docs/focal/retro-log.md`

**Slip reason codes:**

| Code | Meaning |
|------|---------|
| `SCOPE` | Story was larger than estimated |
| `BLOCKED` | External dependency or blocker |
| `LEAVE` | Engineer on leave |
| `TRAVEL` | Engineer travelling |
| `CARRY` | Deliberate carry-over (deprioritised) |
| `REPRIORITY` | Reprioritised in favour of something else |

**Example:**

```
$ python3 focal.py pm retro --repo leninmehedy/my-project --iteration 1
  Iteration I1 (May 18 – May 31) — planned 22 SP

  #43 Implement GitHub OAuth flow — CLOSED ✔
  #44 Add Google OAuth flow — OPEN
    Slip reason [SCOPE/BLOCKED/LEAVE/TRAVEL/CARRY/REPRIORITY]: SCOPE
    Notes: took longer than estimated due to session handling edge cases

  Planned: 22 SP · Delivered: 17 SP · Carry-over: 5 SP
  ✔ docs/focal/retro-log.md updated (I1)
  ✔ Committed
```

**Record appended to `docs/focal/retro-log.md`:**

```markdown
## I1 - May 18 (May 18 – May 31)

### Planned
- @leninmehedy: #43 GitHub OAuth (5 SP) · #44 Google OAuth (5 SP) · ...

### Delivered
- @leninmehedy: #43

### Velocity
- Planned: 22 SP · Delivered: 17 SP · Carry-over: 5 SP

### Slip Reasons
- #44 — SCOPE — took longer than estimated due to session handling edge cases

### Notes
```

---

### `focal pm status`

Print a live terminal summary of the current iteration without opening GitHub.

```
python3 focal.py pm status --repo <owner/repo>
```

**Example output:**

```
Focal Board — Iteration 1 (May 18 – May 31)
─────────────────────────────────────────────
 Delivered   ████████░░░░  12 / 22 SP (55%)
 In progress  2 stories · 5 SP
 Blocked      1 story   · 3 SP
 Not started  3 stories · 2 SP

 Days remaining: 6
 Projected delivery: 17 SP (77%)
```

Reads live from GitHub Issues + Projects. No local state file required.

---

## File structure after `focal pm init`

```
your-repo/
  .github/
    ISSUE_TEMPLATE/
      epic.md               ← GitHub template for epic issues
      story.md              ← GitHub template for story issues
  docs/
    focal/
        epics.md                ← epic/story tracker, updated by focal epic/story create
      iteration-planning.md   ← capacity + schedule, updated by focal pm plan
      retro-log.md            ← velocity history, updated by focal pm retro
      design/                 ← per-feature design records (manual)
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
```

Changes to these files take effect the next time you run `focal pm init` on a new repo.
Existing repos are not affected (files are never overwritten).
