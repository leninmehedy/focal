# Focal Project Management Guide

Focal's `pm` commands let you manage your entire delivery lifecycle — epics, stories,
iteration planning, and retrospectives — using only GitHub Issues, GitHub Projects,
and markdown files in your repo. No external tools, no extra logins, no context switching.

---

## Prerequisites

- `focal board setup` completed — writes `~/.focal/config.json` with your board and account details
- `gh` CLI authenticated with `repo` and `project` scopes

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

**Tip:** run `focal cache refresh-all` (or `focal cache refresh owner/repo`) any time to pull in issues created or
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
focal pm init owner/repo
focal pm epic-create owner/repo
focal pm story-create owner/repo
focal pm plan owner/repo
focal pm retro owner/repo
focal pm status owner/repo
focal pm adopt owner/repo
focal cache refresh owner/repo

# Non-interactive — common flags (see each command section for full reference)
focal pm epic-create owner/repo --title "Title" --description "..." --sp 8
focal pm epic-create owner/repo --from-design docs/focal/design/D001-feature.md
focal pm story-create owner/repo --epic E1 --title "Title" --sp 3
focal pm plan owner/repo --weeks 2 --start 2026-05-19 --team "alice:8,bob:6"
focal pm retro owner/repo --iteration I1 --goal-met --notes "..."
focal pm adopt owner/repo --sp-field "Estimated SP"
focal pm what-if owner/repo --pto "alice:2026-06-27:2026-07-04"
focal pm what-if owner/repo --inject "Urgent fix:8" --reestimate "1.3:13"
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
focal pm init <owner/repo> [--repo-root PATH]
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

**Auto-registers the repo** — after init, the repo is added to `pm_repos` in `~/.focal/config.json` so `focal cache refresh-all` picks it up automatically. To remove a repo from tracking: `focal pm remove-repo owner/repo`.

**Customise templates:** Edit files in `focal/templates/` before running init.
Your changes will be applied to every repo you initialise.

**Example:**

```
$ focal pm init leninmehedy/my-project
  ✔ Label 'epic' ready
  ✔ Label 'story' ready
  ✔ .github/ISSUE_TEMPLATE/epic.md
  ✔ .github/ISSUE_TEMPLATE/story.md
  ✔ docs/focal/epics.md
  ✔ docs/focal/iteration-planning.md
  ✔ docs/focal/retro-log.md
  ✔ docs/focal/design/
  ✔ E0 General Maintenance created (#5)
```

**The General Maintenance epic (E0)**

`focal pm init` automatically creates a standing **E0 General Maintenance** epic on GitHub. This is the permanent home for all unplanned work — bug fixes, security patches, dependency updates, hotfixes, and any task that arrives outside of iteration planning.

| Use E0 when… | Don't use E0 when… |
|---|---|
| A bug is filed against a live release | Work belongs to a defined feature epic |
| An urgent dependency patch is needed | Work was planned in the current iteration |
| CI or tooling breaks mid-sprint | The task has a clear product owner and planned epic |
| Work arrives with no clear epic owner | — |

**Rule: every task needs an issue.** If work doesn't belong to a planned epic, create a story under E0 rather than working without a ticket. E0 is intentionally permanent and never closed — ongoing maintenance always has a home.

User epics start at E1. E0 is reserved exclusively for General Maintenance and is never reassigned.

---

### `focal pm epic-create`

Guided wizard to create a GitHub epic issue and record it in `docs/focal/epics.md`.

```bash
focal pm epic-create <owner/repo> [--repo-root PATH]
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
$ focal pm epic-create leninmehedy/my-project
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
focal pm story-create <owner/repo> [--repo-root PATH]
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
$ focal pm story-create leninmehedy/my-project
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
focal pm plan <owner/repo> [--repo-root PATH] [--refresh]
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
$ focal pm plan leninmehedy/my-project
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
focal pm retro <owner/repo> [--repo-root PATH] [--refresh]
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
$ focal pm retro leninmehedy/my-project
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
focal pm status <owner/repo> [--repo-root PATH] [--refresh]
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

### `focal cache refresh` / `refresh-all` / `status`

The local cache at `docs/focal/.cache/focal-state.json` is the source of truth for
`plan`, `retro`, and `status`. GitHub is always authoritative — the cache is a
read-through for speed.

#### `focal cache status`

Check sync health across all registered PM repos before deciding whether to refresh:

```bash
focal cache status
```

```
Focal cache status  (auto-refresh: enabled  |  limit: 500 issues)

 Repo                     Epics  Stories  Total  Last synced                    Status
 automa-saga/automa-operator      3       18     21  2026-05-16 08:00 UTC (2h ago)  ✔ ok
 automa-saga/automa           5       34     39  2026-05-14 14:00 UTC (2d ago)  ⚠ over limit (201)
```

#### `focal cache refresh-all`

Re-fetch all registered PM repos in one pass. Registered automatically when you run
`focal pm init`:

```bash
focal cache refresh-all           # respects scaling guards (see below)
focal cache refresh-all --force   # bypass all guards
```

#### `focal cache refresh` (single repo)

Re-fetch one specific repo — useful when `refresh-all` skips it due to size, or you
want to refresh one repo immediately without waiting for the scheduler:

```bash
focal cache refresh <owner/repo> [--repo-root PATH]
```

**When to run any of the above:**

- Issues were created or updated directly on GitHub (outside Focal commands)
- Project board statuses were changed manually
- Before `focal pm plan` or `focal pm retro` when you want guaranteed fresh data
  (or use the `--refresh` flag on those commands directly)

**Example:**

```
$ focal cache refresh leninmehedy/my-project
  ✔ Synced 3 epics, 14 stories
  ✔ Last synced: 2026-05-18T09:42:11+00:00
```

#### Scaling controls

For repos with many tracked issues or when you want full manual control, add these
keys to `~/.focal/config.json`:

| Key | Default | Effect |
|---|---|---|
| `auto_cache_refresh` | `true` | Set to `false` to disable the launchd/cron scheduler entirely |
| `max_tracked_issues` | `500` | `refresh-all` skips repos exceeding this tracked issue count |

When `auto_cache_refresh` is false, the scheduler job exits immediately. Refresh
manually on your own schedule:

```bash
focal cache refresh-all --force   # refreshes all repos regardless of limits
```

---

### `focal pm adopt`

Bootstrap the local state cache from existing GitHub issues in a repo that already has epics and stories. Useful when Focal is introduced into a repo that pre-dates Focal, or after a migration.

```bash
focal pm adopt <owner/repo> [--repo-root PATH] [--epic-label LABELS] [--story-label LABELS]
               [--sp-field NAME] [--default-sp N] [--apply] [--normalise] [--prompt-missing]
```

**Dry-run by default.** Pass `--apply` to write files.

**What it does:**

1. Lists all open issues matching the epic and story labels in the repo
2. Resolves hierarchy via sub-issues API, `Part of epic #N` body references, or `[Epic N]` title prefixes
3. Extracts story points from (in priority order): GitHub Projects field → title pattern → body table → prose `**Estimated:** N SP`
4. If `--sp-field` is given, reads that named field on the project board; otherwise tries common field names automatically (`Story Points`, `Estimated SP`, `Estimate`, `SP`, `Points`, `Size`)
5. If `--prompt-missing` is set, prompts interactively for SP on stories where none was found
6. With `--apply`: writes `docs/focal/.cache/focal-state.json` and `docs/focal/epics.md`
7. With `--apply --normalise`: also re-labels issues, moves SP from title to body, creates sub-issue links

**Flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--epic-label LABELS` | `epic` | Comma-separated label(s) that identify epics (e.g. `epic,feature`) |
| `--story-label LABELS` | `story` | Comma-separated label(s) that identify stories (e.g. `story,task`) |
| `--sp-field NAME` | auto-detect | Exact name of the SP field on the project board |
| `--default-sp N` | none | Fallback SP for issues with no estimate |
| `--apply` | off | Write `focal-state.json` and `epics.md`; without this flag runs as dry-run |
| `--normalise` | off | Re-format issues to Focal conventions (requires `--apply`) |
| `--prompt-missing` | off | Prompt for SP on stories that have no estimate |

**Example:**

```
$ focal pm adopt automa-saga/automa --sp-field "Estimated SP" --apply
  Discovering issues...
  Found 5 epics, 34 stories
  Resolved hierarchy: 34/34 stories linked to epics
  SP extracted: 31/34  (3 missing)
  ✔ docs/focal/epics.md written
  ✔ focal-state.json written
  ✔ Committed
```

With custom labels and a fallback SP:

```
$ focal pm adopt automa-saga/automa --epic-label "epic,feature" --default-sp 3 --apply
```

With `--prompt-missing`:

```
$ focal pm adopt automa-saga/automa --prompt-missing --apply
  ...
  SP missing for: #88 "Implement retry logic" — estimate (SP): 3
  SP missing for: #91 "Add integration test" — estimate (SP): 2
```

---

### `focal pm design`

Manage design docs in `docs/focal/design/`. Currently used to list all design docs with their status and linked epic.

```bash
focal pm design [--repo-root PATH] [--status STATUS] [--update-index]
```

Run from inside the repo root, or pass `--repo-root` explicitly.

**What it does:**

Lists all `D*.md` files in `docs/focal/design/`, reading YAML frontmatter to display status, title, and linked epic number:

```
$ focal pm design

  ID     Title                          Status    Epic
  D001   What-if impact assessment      Active    #69
  D002   Board sync engine v2           Planned   —
  D003   Auth middleware refactor       Draft     —
```

Filter by status:

```
$ focal pm design --status Active
```

Regenerate `docs/focal/design/INDEX.md`:

```
$ focal pm design --update-index
```

**Design doc lifecycle:**

| Status | Meaning |
|--------|---------|
| `Draft` | Being written — no backlog items created yet |
| `Planned` | Design approved — ready for `--from-design` |
| `Active` | Epic created — delivery in progress |
| `Done` | All stories closed |
| `Archived` | Withdrawn before implementation |

`focal pm epic-create --from-design` automatically advances the status from `Planned` → `Active` and records the epic number in frontmatter.

---

### `focal pm what-if`

Dry-run simulation of the iteration plan under hypothetical scenarios. Shows which stories slip to later iterations without modifying any files.

```bash
focal pm what-if <owner/repo> [--repo-root PATH] \
  [--pto "HANDLE:FROM:TO"] \
  [--inject "TITLE:SP"] \
  [--reestimate "STORY_ID:SP"] \
  [--apply]
```

**Scenarios** (one or more; all are combinable):

| Flag | Format | Effect |
|------|--------|--------|
| `--pto` | `handle:YYYY-MM-DD:YYYY-MM-DD` | Reduce capacity for the handle over the date range |
| `--inject` | `"Title:SP"` | Inject a high-priority story at the top of the backlog |
| `--reestimate` | `STORY_ID:SP` | Change a story's SP and ripple the change through all iterations |

All flags are repeatable — pass multiple `--pto` for multiple people, etc.

**Dry-run by default.** Pass `--apply` to write the updated `iteration-planning.md` and commit it.

**How capacity reduction works for `--pto`:**
Focal counts working days (Mon–Fri) in the overlap between the PTO window and each iteration window, then subtracts `(overlap_days / 10) × sp_per_iter` from that iteration's capacity.

**Example — PTO impact:**

```
$ focal pm what-if automa-saga/automa --pto "alice:2026-06-27:2026-07-04"

  ◎  Focal — what-if (automa-saga/automa)

Scenario
  PTO  @alice  2026-06-27 – 2026-07-04

Impact by iteration
Iter  Orig SP  Sim SP  Cap  Slipped out      Added in
I3         18      18   12  1.5, 1.7         —
I4         14      16   14  —                1.5, 1.7

Summary
  2 story slot(s) slipped across 1 iteration(s)

Capacity changes
  I3  @alice PTO 2026-06-27 – 2026-07-04 (−4 SP)

  Dry run — pass --apply to write updated iteration-planning.md
```

**Example — inject + reestimate:**

```
$ focal pm what-if automa-saga/automa \
    --inject "Urgent security patch:8" \
    --reestimate "1.3:13"

  ◎  Focal — what-if (automa-saga/automa)

Scenario
  Inject  'Urgent security patch'  8 SP
  Re-estimate  1.3:  5 SP → 13 SP

Impact by iteration
...
```

**Tip:** run `focal pm plan` first if `iteration-planning.md` does not yet exist — `what-if` reads it as its baseline.

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
