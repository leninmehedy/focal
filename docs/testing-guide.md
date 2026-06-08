# Focal Beta Testing Guide

This guide covers every command in Focal. For each command there is a list of test cases — what to run, what to look for, and what constitutes a pass or fail.

---

## Before you start

### Prerequisites

- **macOS or Linux** (Windows not yet tested)
- **Python 3.10+** — `python3 --version`
- **GitHub CLI (`gh`)** — authenticated with `repo` and `project` scopes:
  ```bash
  brew install gh        # macOS; or see https://cli.github.com for Linux
  gh auth login
  gh auth refresh -s project
  gh auth status         # should show: Logged in + repo, project scopes
  ```
- **At least one GitHub repo** with open issues assigned to you
- A **GitHub Projects v2 board is not required** — the setup wizard can create one automatically

### How to install

**Option A — pipx (recommended for beta testers)**

This is the intended end-user experience. `pipx` installs `focal` into an isolated
environment so it doesn't conflict with anything else.

```bash
# Install pipx if you don't have it
pip3 install pipx
pipx ensurepath
# Restart your terminal, then:

pipx install focal-cli
focal --version        # should print the installed version
```

**Option B — git clone + editable install (recommended for contributors / debugging)**

Use this if you want to poke at the source, reproduce a bug, or test unreleased changes.

```bash
git clone https://github.com/leninmehedy/focal.git
cd focal
pip3 install -e .      # adds 'focal' to your PATH via the current checkout
focal --version
```

> On macOS you may need `pip3 install -e . --break-system-packages` if Python was
> installed via Homebrew without a virtual environment.

**Notation used in this guide:**
- ✅ Expected pass — the test should succeed with this output
- ❌ Expected failure — the command should fail gracefully with a clear error, not a traceback

---

## Installation

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| I1 | pipx install | `pipx install focal-cli` | Installs cleanly, no errors ✅ |
| I2 | focal command available | `which focal` after I1 | Path returned (e.g. `~/.local/bin/focal`) — not "not found" ✅ |
| I3 | focal --version | `focal --version` | Prints the installed version (e.g. `1.10.2`) ✅ |
| I4 | focal --help | `focal --help` | Usage text with all command groups: `board`, `pm`, `cache`, `reset` ✅ |
| I5 | Editable install | `git clone https://github.com/leninmehedy/focal.git && cd focal && pip3 install -e . && focal --version` | Same version output as I3 ✅ |
| I6 | Upgrade | `pipx upgrade focal-cli` | Upgrades to latest version; `focal --version` shows new version ✅ |
| I7 | Uninstall | `pipx uninstall focal-cli` | `focal` command no longer found ✅ |

---

## Setup

### `focal board setup`

The interactive wizard that creates `~/.focal/config.json`.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| S1 | Fresh setup — auto-create board | `focal board setup` with no existing config, choose **1** (Create a new board) | Prompts for GitHub username and board title. Creates a Projects v2 board, adds recommended Status columns, then continues to repo selection. Creates `~/.focal/config.json` ✅ |
| S2 | Fresh setup — use existing board | `focal board setup` with no existing config, choose **2** (I already have a board) | Prompts for board URL, GitHub username, Done column name, repos. Creates `~/.focal/config.json` ✅ |
| S3 | Config file location | After S1 or S2, `cat ~/.focal/config.json` | File exists at `~/.focal/config.json` (not in the focal repo directory) ✅ |
| S4 | Board created on GitHub | After S1 | New board visible at `https://github.com/users/YOUR_USERNAME/projects` with Status field containing 7 recommended options ✅ |
| S5 | Re-run wizard — add repos | Re-run `focal board setup` when config already exists | Offers 4 choices: **Add repos**, **Edit repo list**, **Full reconfigure**, **Cancel**. Choosing "Add repos" appends to the `repos` array without touching other settings ✅ |
| S6 | Re-run wizard — full reconfigure | Choose "Full reconfigure" in S5 | Overwrites config from scratch ✅ |
| S7 | Cancel re-run | Choose "Cancel" when offered options | Exits cleanly with no changes ✅ |
| S8 | Status map created | After setup with mismatched status columns | `~/.focal/status_map.json` is created with translation mappings ✅ |
| S9 | Non-interactive — create board | `focal board setup --owner USER --repos owner/repo --create-board --board-title "My Board"` with no existing config | Runs without any prompts. Creates a new GitHub Projects board, writes `~/.focal/config.json` ✅ |
| S10 | Non-interactive — attach existing board | `focal board setup --owner USER --repos owner/repo --use-board --use-board-number N` | Runs without prompts. Reads Status field from existing board, writes config ✅ |
| S11 | Non-interactive — assignee default | `focal board setup --owner USER --repos owner/repo --create-board` (no `--assignee`) | `assignee` in config equals `owner` value ✅ |
| S12 | Non-interactive — partial flags fall through | `focal board setup --owner USER` (repos not given) | Falls through to interactive mode for missing values ✅ |
| S13 | Canonical columns created — interactive | Run S1 (create board, interactive) | After board creation, board has exactly 7 Status columns: 🆕 New, 📋 Backlog, 🔖 Ready, 🏗 In progress, ✋ Blocked, 👀 In review, ✅ Done — not GitHub defaults ✅ |
| S14 | Canonical columns created — non-interactive | Run S9 (`--create-board`) | Same 7 canonical columns set on the new board; terminal prints `✔ Status columns set: 🆕 New, ...` ✅ |

---

## Board sync

### `focal board sync`

Bidirectional sync between your personal board and origin repo project boards.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| BS1 | Basic sync | `focal board sync` | Runs without error. Last log line: `Sync complete — added: N  inherited: N  pushed: N  stale: N` ✅ |
| BS2 | Issues appear on board | After BS1, open `https://github.com/users/YOUR_USERNAME/projects/N` | All open issues assigned to you across configured repos are visible on the board ✅ |
| BS3 | Incremental sync | Run sync twice in a row | Second run output includes `(incremental)` and is faster; issues unchanged since first run are not re-fetched ✅ |
| BS4 | Status inheritance | Add a new issue (assigned to you) to a repo that has its own project board | After sync, new issue appears on personal board with status matching the origin project ✅ |
| BS5 | Push to origin | Move a card on your personal board, then sync | The status change is pushed to origin project boards the issue belongs to ✅ |
| BS6 | Stale handling | Close or unassign an issue that is on your board, then sync | Issue is moved to Done column on personal board ✅ |
| BS7 | No config | Delete `~/.focal/config.json`, then `focal board sync` | Clear error: `Focal is not configured. Run focal board setup ...` — no traceback ❌ |
| BS8 | Desktop notification (macOS) | After sync completes | macOS notification appears: "Focal sync complete" with counts ✅ |
| BS9 | Disable notification | Set `"notifications": false` in `~/.focal/config.json`, sync again | No notification fires ✅ |
| BS10 | Log file created | After sync | `~/.focal/logs/YYYY-MM-DD.log` exists and contains sync output ✅ |

### `focal board status`

Live board summary — no sync, just reads current state.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| ST1 | Basic status | `focal board status` | Status count table (one row per column + Total), "By repo" breakdown, blocked/recent sections if applicable ✅ |
| ST2 | By-repo breakdown | After sync with issues from multiple repos | "By repo" section lists each `owner/repo` with total count and per-status breakdown on the same line ✅ |
| ST3 | Blocked items shown | Have at least one issue in a "Blocked" status column | Blocked section appears with `owner/repo#N — title` and the issue URL on the next line ✅ |
| ST4 | Recently added shown | Have issues added to board in last 7 days | "Recently added" section shows `owner/repo#N — title (status)` ✅ |
| ST5 | No config | Delete `~/.focal/config.json`, then run | Clear error: `Focal is not configured.` — no traceback ❌ |
| ST6 | Empty board | Run on a newly created board with no items | Status table shows Total: 0, no By-repo/blocked/recent sections ✅ |
| ST7 | Ref format | Check any issue line in the output | Issues shown as `owner/repo#N` not bare `#N` ✅ |

---

## Reset

### `focal reset`

Removes all Focal config, state, logs, and launchd/cron plists.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| R1 | Interactive prompt | `focal reset` | Lists files to delete and asks for confirmation ✅ |
| R2 | Cancel | Answer `n` at prompt | Nothing is deleted ✅ |
| R3 | Confirm deletion | Answer `y` at prompt | `~/.focal/config.json`, `~/.focal/status_map.json`, `~/.focal/state.json`, `~/.focal/logs/` are removed ✅ |
| R4 | Skip prompt | `focal reset --yes` | Deletes immediately without confirmation prompt ✅ |
| R5 | launchd cleanup (macOS) | With a loaded focal plist, run `focal reset --yes` | `launchctl unload` is called on matching plists and plist files are deleted ✅ |
| R6 | Missing files | Run reset when some files are already missing | Completes cleanly — skips missing files silently ✅ |
| R7 | Post-reset message | After reset | Prints: `✔ Reset complete. Run 'focal board setup' to reconfigure.` ✅ |

---

## Project management

### `focal pm init`

Bootstraps a repo with Focal PM structure.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| PI1 | Basic init | `focal pm init owner/repo --repo-root /path/to/repo` | Creates `.github/ISSUE_TEMPLATE/epic.md`, `.github/ISSUE_TEMPLATE/story.md`, `docs/focal/epics.md`, `docs/focal/iteration-planning.md`, `docs/focal/retro-log.md`, `docs/focal/design/`. Labels `epic` and `story` created on GitHub ✅ |
| PI2 | Auto-registers repo | After PI1, `cat ~/.focal/config.json` | `pm_repos` array contains `{"repo": "owner/repo", "repo_root": "/path/to/repo"}` ✅ |
| PI3 | General Maintenance epic created | After PI1, `gh issue list --repo owner/repo --label epic` | Issue titled "General Maintenance" exists with label `epic`. `docs/focal/epics.md` contains `## E0 — General Maintenance` ✅ |
| PI4 | E0 is idempotent | Run `focal pm init owner/repo` again on same repo | No second E0 issue created; output shows `E0 General Maintenance already exists — skipping` ✅ |
| PI5 | User epics start at E1 | After PI3, run `focal pm epic-create owner/repo --title "My Epic" --sp 5` | New epic gets ID E1 (not E0) ✅ |
| PI6 | Safe to re-run (files) | Run init again on same repo | Existing files not overwritten; re-run exits cleanly ✅ |
| PI7 | No board setup — warning banner | Run `focal pm init owner/repo` without `~/.focal/config.json` | Command succeeds (no error). Output contains a yellow ⚠ banner: "No board configured yet. Run focal board setup …" ✅ |
| PI8 | No board setup — step 0 in next-steps | Run `focal pm init owner/repo` without `~/.focal/config.json` | Next-steps section shows step 0 as `focal board setup`, other steps renumbered 1, 2, 3 ✅ |
| PI9 | Board configured — no banner | Run `focal pm init owner/repo` with `~/.focal/config.json` present | No step-0 or warning banner in output; steps start at 1 ✅ |
| PI10 | Repo not found | `focal pm init nonexistent/repo` | Prints `Error: Repository nonexistent/repo not found on GitHub.` and exits non-zero; no local files created ✅ |

### `focal pm adopt-plan`

Bootstrap GitHub issues from `docs/focal/plan.md`. Dry-runs by default; pass `--apply` to create issues.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| AP1 | Dry-run output | `focal pm adopt-plan owner/repo` (after `focal pm init`) | Prints table of epics and stories to create; no GitHub issues created; `epics.md` unchanged ✅ |
| AP2 | Apply creates epics | `focal pm adopt-plan owner/repo --apply` | GitHub issues created for every epic in `plan.md` not already in `focal-state.json`; `docs/focal/epics.md` re-rendered ✅ |
| AP3 | Apply creates stories | After AP2, `gh issue list --repo owner/repo --label story` | Story issues created, linked as sub-issues to their parent epic ✅ |
| AP4 | Idempotent | Run `focal pm adopt-plan owner/repo --apply` a second time | "Nothing to create" message; no new issues; `epics.md` unchanged ✅ |
| AP5 | Custom plan path | `focal pm adopt-plan owner/repo --from-plan /tmp/my-plan.md --apply` | Uses the specified file instead of `docs/focal/plan.md` ✅ |
| AP6 | Missing plan.md | `focal pm adopt-plan owner/repo --apply` (no `plan.md`) | Clear error: "Plan doc not found. Run focal pm init first…" ✅ |
| AP7 | epics.md re-rendered on epic-create | `focal pm epic-create owner/repo --title "New Epic" --sp 3` | `docs/focal/epics.md` regenerated from state; new epic appears; `<!-- focal-managed -->` header present ✅ |
| AP8 | epics.md re-rendered on story-create | `focal pm story-create owner/repo --epic E1 --title "New Story" --sp 2` | `docs/focal/epics.md` regenerated; new story row appears under E1 ✅ |

### `focal pm triage`

List open issues not linked to any epic in local state.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| TR1 | Basic output | `focal pm triage owner/repo` | Rich table of untracked open issues: number, title, labels, assignee, age; hint to run `focal pm story-create` ✅ |
| TR2 | Nothing untracked | Run after all issues are linked | "✓ No untracked issues — everything is linked to an epic." ✅ |
| TR3 | `--label` filter | `focal pm triage owner/repo --label bug` | Only issues with the `bug` label shown ✅ |
| TR4 | `--unassigned` filter | `focal pm triage owner/repo --unassigned` | Only issues with no assignee shown ✅ |
| TR5 | `--json` flag | `focal pm triage owner/repo --json` | Valid JSON array; each item has `number`, `title`, `labels`, `assignees`, `created_at` ✅ |

### `focal pm epic-create`

Creates a GitHub epic issue.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| EC1 | Interactive | `focal pm epic-create owner/repo` | Prompts for title, description, SP. Creates a GitHub issue with label `epic`. Adds to personal board with SP set. Appends to local state cache ✅ |
| EC2 | Non-interactive | `focal pm epic-create owner/repo --title "My Epic" --description "Desc" --sp 13` | Creates issue without any prompts. Prints epic ID (E1, E2, …) and GitHub URL ✅ |
| EC3 | ID increments | Create two epics | First gets `E1`, second gets `E2` ✅ |
| EC4 | State cache updated | After EC2, `cat docs/focal/.cache/focal-state.json` in the target repo | Epic entry present with correct `issue_number`, `sp`, `status: "open"` ✅ |
| EC5 | No board setup | Run without config | Clear error ❌ |
| EC6 | From design doc | `focal pm epic-create owner/repo --from-design docs/focal/design/D001-foo.md --repo-root .` | Prints dry-run summary (epic title, SP, story list), asks for confirmation, creates epic + all stories, links stories as sub-issues, sets SP on board, rewrites design doc frontmatter to `status: Active` and adds `epic: <N>` ✅ |
| EC7 | From design — no breakdown | `--from-design` on a doc with no `## Breakdown hint` section | Clear error: "No '## Breakdown hint' section found" — no traceback ❌ |
| EC8 | From design — design not found | `--from-design non-existent.md` | Clear error: "Design doc not found" ❌ |
| EC9 | From design — design still Draft | `--from-design` on a doc with `status: Draft` | Command proceeds; prints current status in dry-run summary; frontmatter updated to Active ✅ |

### `focal pm story-create`

Creates a story issue linked to an epic.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| SC1 | Interactive | `focal pm story-create owner/repo` | Prompts for epic (shows list), title, description, SP. E0 General Maintenance is listed with a `(bugs & unplanned work)` tag. Hint printed: "No matching epic? Use E0 General Maintenance for bugs and unplanned work." ✅ |
| SC2 | Non-interactive | `focal pm story-create owner/repo --epic E1 --title "My Story" --description "Desc" --sp 5` | Creates issue with label `story`, linked as sub-issue of the epic. Story ID is `1.1`, `1.2`, etc. ✅ |
| SC3 | Create story under E0 | `focal pm story-create owner/repo --epic E0 --title "Fix login crash" --sp 3` | Creates story under General Maintenance epic. Story ID is `0.1`, linked as sub-issue of E0 issue ✅ |
| SC4 | Sub-issue link | After SC2, open epic on GitHub | Story appears in the sub-issues list of the epic ✅ |
| SC5 | SP on board | After SC2, open personal board | Story card has SP value set in the Estimate/SP field ✅ |
| SC6 | Wrong epic ID | `--epic E99` on a repo with no E99 | Clear error: epic not found — no traceback ❌ |

### `focal pm plan`

Generates `docs/focal/iteration-planning.md` from the local state cache.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| PL1 | Basic plan | `focal pm plan owner/repo --weeks 2 --start 2026-06-02 --team "alice:8,bob:6"` | Creates `docs/focal/iteration-planning.md` with iteration schedule, capacity, SP allocation, risk section ✅ |
| PL2 | PTO reduction | `--pto "alice:2026-06-09:2026-06-13"` | Alice's capacity reduced proportionally for that iteration ✅ |
| PL3 | Goal labels | `focal pm plan owner/repo --weeks 2 --start 2026-06-02 --team "alice:8" --goals "I1:Ship auth,I2:Close E2"` | Each iteration section in `iteration-planning.md` contains a `**Goal:** <text>` line immediately after the heading ✅ |
| PL3b | Goals not provided | Run without `--goals` | Goal prompts appear interactively; blank answers produce no `**Goal:**` line in the doc ✅ |
| PL3c | Partial goals | `--goals "I1:Ship auth"` with two iterations | I1 shows `**Goal:** Ship auth`; I2 has no Goal line ✅ |
| PL4 | Interactive | Run without flags | Prompts for each input ✅ |
| PL5 | With refresh | `--refresh` flag | Fetches latest state from GitHub before planning ✅ |
| PL6 | Empty backlog | Run with no epics/stories in cache | Warns that backlog is empty, exits cleanly ✅ |

### `focal pm retro`

Closes out an iteration and appends to `docs/focal/retro-log.md`.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| RE1 | Basic retro | `focal pm retro owner/repo --iteration I1 --goal-met --went-well "Good collab" --to-improve "Estimates" --notes "Good sprint"` | Appends iteration block to `docs/focal/retro-log.md` with delivered vs carry-over, velocity metrics ✅ |
| RE2 | Goal not met | `--no-goal-met` | Record shows `Goal met: ❌ No` ✅ |
| RE3 | Multiple went-well/improve | Pass `--went-well` and `--to-improve` multiple times | All items appear in the retro block ✅ |
| RE4 | Action items | `--action "alice:Re-estimate carry-overs:2026-06-10"` | Action item with assignee and due date appears in the record ✅ |
| RE5 | Delivered vs carry-over | Have some iteration stories closed on GitHub, some still open | Closed stories listed as delivered, open stories as carry-over ✅ |
| RE6 | Velocity calculated | After RE1, check retro-log.md | `Planned`, `Delivered`, `Carry-over` SP values are correct ✅ |
| RE7 | Interactive | Run without flags | Prompts for iteration selection, goal met, retrospective items ✅ |

### `focal pm status`

Live terminal dashboard of the current iteration.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| PS1 | Single repo | `focal pm status owner/repo` | Shows progress bar, SP delivered vs planned, story list with assignee and status ✅ |
| PS2 | All repos (no arg) | `focal pm status` with multiple repos registered via `focal pm init` | Prints status panel for each registered PM repo sequentially, auto-detecting current iteration for each ✅ |
| PS3 | No PM repos registered | `focal pm status` with no `pm_repos` in config | Friendly message: "No PM repos registered. Run focal pm init ..." ✅ |
| PS4 | Missing repo_root | Registered repo whose local path no longer exists | Skips that repo with a dim "Skipping … repo_root not found" message, continues to next ✅ |
| PS5 | With refresh | `focal pm status owner/repo --refresh` | Fetches latest GitHub state before displaying ✅ |
| PS6 | Blocked stories | Have a story in "Blocked" status | Blocked stories highlighted separately ✅ |
| PS7 | No iterations planned | Run before `focal pm plan` | Friendly message: no active iteration found ✅ |

### `focal pm velocity`

Historical velocity table from `docs/focal/retro-log.md`.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| V1 | Basic velocity | `focal pm velocity owner/repo` (after at least one retro) | Rich table with one row per iteration: label, goal met, capacity SP, planned SP, delivered SP, carry-over SP, efficiency % ✅ |
| V2 | Average row | After 2+ retros | Bottom row shows averages across all iterations ✅ |
| V3 | Footer totals | | One-line footer: `N iterations · X SP delivered · avg carry-over: Y SP/iter` ✅ |
| V4 | No retro-log.md | Run before any retro | Friendly message: no retro data found — no traceback ✅ |
| V5 | Empty retro-log.md | File exists but has no iteration blocks | Same friendly message as V4 ✅ |

### `focal pm adopt`

Onboards an existing repo's issues into Focal PM state.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| AD1 | Dry run | `focal pm adopt owner/repo` | Prints epics + stories tables with focal IDs, SP, hierarchy links. No files written. Footer: "Dry run — pass --apply" ✅ |
| AD2 | Apply | `focal pm adopt owner/repo --apply --repo-root .` | Writes `docs/focal/.cache/focal-state.json`. Epics and stories have `focal_id`, `issue_number`, `sp`, `status` ✅ |
| AD3 | Custom labels | `focal pm adopt owner/repo --epic-label "epic,feature" --story-label "story,task"` | Discovers issues with either label; both treated as epics/stories respectively ✅ |
| AD4 | SP auto-detect | Repo has issues with "Estimated SP" project field | SP populated from field without needing `--sp-field` ✅ |
| AD5 | SP fallback | `--default-sp 3` on a repo with no SP anywhere | All missing estimates set to 3 ✅ |
| AD6 | Prompt missing | `--prompt-missing` on repo with some unestimated issues | Interactively prompts once per unestimated issue; SP recorded in output ✅ |
| AD7 | Orphaned stories | Stories with no epic linkage | Reported as orphaned in warnings; added to synthetic `E0` in state when `--apply` ✅ |
| AD8 | Normalise | `--apply --normalise` | Re-labels issues, moves SP from title to body table, creates sub-issue links for inferred hierarchy ✅ |
| AD9 | Idempotent | Run `--apply` twice | Second run does not duplicate epics or stories in state cache ✅ |

### `focal pm design`

Lists design docs in `docs/focal/design/`.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| DS1 | List all | `focal pm design` (run from repo root) or `focal pm design --repo-root PATH` | Table grouped by status (Draft → Planned → Active → Done → Archived); shows ID, title, epic ref, updated date ✅ |
| DS2 | Filter by status | `focal pm design --status Active` | Only Active docs shown ✅ |
| DS3 | Update index | `focal pm design --update-index` | Regenerates `docs/focal/design/INDEX.md` from current design docs ✅ |
| DS4 | No design dir | `focal pm design` on repo without `docs/focal/design/` | Friendly message: no design directory found ✅ |
| DS5 | In pm status | `focal pm status owner/repo` | Footer includes one line per Draft/Planned/Active design doc ✅ |

### `focal pm what-if`

Simulates what happens to the iteration plan under a hypothetical scenario.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| WI1 | No scenario | `focal pm what-if owner/repo` | Clear message: "No scenario specified. Use --pto, --inject, or --reestimate." ❌ |
| WI2 | PTO dry-run | `focal pm what-if owner/repo --pto alice:2026-06-02:2026-06-06` | Impact table shows reduced capacity for affected iterations; stories that no longer fit listed as "slipped out"; dry-run footer ✅ |
| WI3 | Inject dry-run | `focal pm what-if owner/repo --inject "P1 fix:8"` | INJ1 appears in "added in" for the earliest iteration with capacity; stories displaced show as "slipped out" ✅ |
| WI4 | Re-estimate dry-run | `focal pm what-if owner/repo --reestimate 1.3:13` | Story 1.3 SP updated; ripple reflected in iteration assignments; summary shows slipped count ✅ |
| WI5 | Combined scenario | `--pto alice:... --inject "Fix:5" --reestimate 1.2:8` | All three scenarios applied; report shows combined impact ✅ |
| WI6 | Apply | `focal pm what-if owner/repo --pto alice:... --apply` | `docs/focal/iteration-planning.md` overwritten with simulated plan; git commit created ✅ |
| WI7 | No plan file | Run before `focal pm plan` | Clear error: "No iteration plan found… Run focal pm plan first." ❌ |
| WI8 | Unknown PTO handle | `--pto unknownuser:2026-06-02:2026-06-06` | No capacity change (handle not in team); no error ✅ |
| WI9 | Bad flag format | `--pto alice-only` | Clear error showing expected format ❌ |

### `focal pm remove-repo`

Unregisters a repo from PM tracking.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| RR1 | Remove registered repo | `focal pm remove-repo owner/repo` | Entry removed from `pm_repos` in `~/.focal/config.json`. Confirmation printed ✅ |
| RR2 | Remove unregistered repo | Run on a repo not in `pm_repos` | Clear message: repo not found in pm_repos — exits cleanly ✅ |
| RR3 | Local files untouched | After RR1, check the repo directory | `docs/focal/` and state cache are not deleted ✅ |
| RR4 | No longer in refresh-all | After RR1, `focal cache refresh-all` | Removed repo is not processed ✅ |

---

## Cache

### `focal cache refresh`

Re-fetches state for one repo from GitHub.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| CR1 | Basic refresh | `focal cache refresh owner/repo --repo-root /path/to/repo` | Fetches epic/story state from GitHub. Prints count of synced epics/stories. Updates `last_synced` in state file ✅ |
| CR2 | Reflects closed issues | Close an issue on GitHub, then refresh | Issue `status` in cache changes from `open` to `closed` ✅ |
| CR3 | Project status updated | Move a story card on GitHub project board, then refresh | `project_status` field updated in cache ✅ |
| CR4 | No cache file | Run on repo that hasn't had `focal pm init` | Graceful error: no state cache found ❌ |

### `focal cache refresh-all`

Re-fetches all registered PM repos.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| CA1 | Basic refresh-all | `focal cache refresh-all` | Processes all repos in `pm_repos`. Summary line per repo ✅ |
| CA2 | Force flag | `focal cache refresh-all --force` | Bypasses `auto_cache_refresh` and `max_tracked_issues` guards ✅ |
| CA3 | Over limit skipped | Set `max_tracked_issues: 5` in config, have a repo with more epics+stories | That repo is skipped with a warning ✅ |
| CA4 | Disabled scheduler | Set `auto_cache_refresh: false` | `refresh-all` without `--force` skips all repos with message ✅ |
| CA5 | No pm_repos | Run with empty `pm_repos` | Friendly message: no repos registered — run `focal pm init` first ✅ |

### `focal cache status`

Shows cache health across all registered repos.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| CS1 | Basic status | `focal cache status` | Rich table: repo, last synced (relative time), epic count, story count, total vs limit, health indicator ✅ |
| CS2 | Stale indicator | Repo not refreshed in 24+ hours | Row shows warning indicator (⚠) ✅ |
| CS3 | Over-limit indicator | Repo with tracked issues > `max_tracked_issues` | Row shows warning indicator ✅ |
| CS4 | No pm_repos | Empty `pm_repos` | Friendly message: no repos registered ✅ |

---

## Solo mode (`focal pm solo`)

State lives in `docs/focal/build-log.json`. `docs/build-log.md` is rendered from it — never hand-edited.

### `focal pm solo init`

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| S1 | Basic init | `focal pm solo init owner/repo --repo-root /path/to/repo` | Creates `docs/focal/build-log.json` with empty sections; renders `docs/build-log.md` ✅ |
| S2 | Idempotent | Run init twice | Second run prints "already exists — skipping" for JSON; re-renders MD ✅ |

### `focal pm solo queue / start / pr / ship`

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| S3 | Queue item | `focal pm solo queue "#10" feat/10-my-feature --sp 3 --what "my feature"` | Row appears in `up_next` in JSON; rendered in `## Up next` in MD ✅ |
| S4 | Start item | `focal pm solo start "#10"` | Row moves from `up_next` → `in_flight`; PR shows `—`, State shows `🔄` ✅ |
| S5 | Set PR | `focal pm solo pr "#10" 42` | `in_flight` row updated: `pr` becomes `#42` ✅ |
| S6 | Ship item | `focal pm solo ship "#10"` | Row moves from `in_flight` → prepended to `shipped`; `## In flight` is empty ✅ |
| S7 | Queue idempotent | Queue same issue twice with different SP | Second call updates existing row — no duplicate ✅ |
| S8 | Start missing issue | `focal pm solo start "#999"` (not in up_next) | Error: "#999 not found in Up next" ✅ |

### `focal pm solo note`

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| S9 | Update note | `focal pm solo note "PR #42 open on feat/10-my-feature"` | `current_state.last_action` updated in JSON; visible in `## Current state` in MD ✅ |

### `focal pm solo status`

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| S10 | Basic status | `focal pm solo status owner/repo` | Renders in-flight, up-next, shipped (last 5) from JSON ✅ |
| S11 | Custom last | `focal pm solo status --last 3` | Shipped section shows only 3 rows ✅ |
| S12 | Empty sections | Run on freshly init'd repo | Shows "Nothing in flight", "Nothing up next", "Nothing shipped yet" ✅ |
| S13 | Missing JSON | Run before init | Error with hint to run `focal pm solo init` ✅ |

### `focal pm solo render`

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| S14 | Render | `focal pm solo render` | Re-generates `docs/build-log.md` from JSON; idempotent ✅ |

### `focal pm epics-render`

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| ER1 | Basic render | `focal pm epics-render` | Re-generates `docs/focal/epics.md` from `focal-state.json`; prints `✔ docs/focal/epics.md rendered` ✅ |
| ER2 | Idempotent | Run twice | Second run produces identical file; no error ✅ |
| ER3 | Reflects closed issues | Close an issue via `gh issue close`, then run | Closed issue shows ✅ in `epics.md` ✅ |
| ER4 | Custom repo-root | `focal pm epics-render --repo-root /path/to/repo` | Renders epics.md in the specified repo ✅ |

### `focal pm solo sync`

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| SR1 | Basic sync | `focal pm solo sync owner/repo` | Fetches last 10 releases; `releases` array populated in `build-log.json`; `## Releases` section rendered in `build-log.md` ✅ |
| SR2 | Custom limit | `focal pm solo sync owner/repo --limit 3` | Only 3 releases fetched ✅ |
| SR3 | Status shows releases | `focal pm solo status owner/repo` after sync | Releases panel shows last 5 releases; latest version + date shown below table ✅ |
| SR4 | No releases repo | Sync a repo with no GitHub releases | Releases section shows empty table; no error ✅ |
| SR5 | Idempotent | Run sync twice | Second run overwrites with fresh data — no duplicates ✅ |

---

## MCP server (`focal mcp serve` / `focal skill install`)

### `focal skill install`

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| MCP1 | Install for Claude | `focal skill install claude` | `~/.claude/settings.json` updated; `mcpServers.focal` entry present with `"command": "focal", "args": ["mcp", "serve"]` ✅ |
| MCP2 | Install for Cursor | `focal skill install cursor` | `~/.cursor/mcp.json` updated with same entry ✅ |
| MCP3 | Auto-detect | `focal skill install` (auto) | Detects installed tool and writes to correct config ✅ |
| MCP4 | Idempotent | Run `focal skill install claude` twice | Second run prints "already installed" — no duplicate entries ✅ |
| MCP5 | Unknown target | `focal skill install vscode` | Clear error listing supported targets ❌ |

### `focal mcp serve` (tool smoke tests)

Run in Claude Code after `focal skill install claude` with `focal` configured:

| # | Test | How to invoke | Expected result |
|---|------|--------------|-----------------|
| MCP6 | Board sync | Ask agent: "sync my focal board" → agent calls `focal_board_sync` | Returns `{"ok": true, "added": N, "stale": N, ...}` ✅ |
| MCP7 | Board setup | Ask agent: "set up focal with owner X, assignee Y, repos [Z]" → `focal_board_setup` | Returns `{"ok": true}`, `~/.focal/config.json` created ✅ |
| MCP8 | PM init | Agent calls `focal_pm_init(repo="org/repo", repo_root=".")` | Returns `{"ok": true, "repo": "org/repo"}` ✅ |
| MCP9 | Epic create | Agent calls `focal_pm_epic_create(repo="org/repo", title="...", description="...", sp=8)` | Returns `{"ok": true, "issue_number": N, "url": "..."}` ✅ |
| MCP10 | Story create | Agent calls `focal_pm_story_create(repo="org/repo", epic_id="E1", title="...", description="...", sp=3)` | Returns `{"ok": true, "story_id": "1.1", ...}` ✅ |
| MCP11 | PM status | Agent calls `focal_pm_status(repo="org/repo")` | Returns iteration stats dict with `ok: true` ✅ |
| MCP12 | Design list | Agent calls `focal_pm_design_list(repo_root=".")` | Returns list of design doc metadata ✅ |
| MCP13 | Cache refresh | Agent calls `focal_cache_refresh(repo="org/repo")` | Returns `{"ok": true, "epics": N, "stories": N}` ✅ |
| MCP14 | Cache status | Agent calls `focal_cache_status()` | Returns per-repo sync health dict ✅ |
| MCP15 | Not configured | Call any board tool before `focal board setup` | Returns `{"ok": false, "error": "Not configured..."}` ❌ |

### Unit tests

```
pytest tests/test_mcp_server.py -v
```

Expected: 10 tests pass covering `_cfg_dict`, error paths for `focal_board_sync`, `focal_pm_status`, `focal_pm_design_list`, `focal_cache_status`, `focal_pm_whatif`.

---

## Scheduler (macOS launchd)

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| SCH1 | Install board sync | Copy and load `launchd/com.your-username.focal.plist` | `launchctl list \| grep focal` shows the job. Sync runs on the hour ✅ |
| SCH2 | Install cache refresh | Copy and load `launchd/com.your-username.focal-cache.plist` | Job runs at 08:00 and 14:00. Log file updated after each run ✅ |
| SCH3 | Log rotation | Run for multiple days | One log file per day in `~/.focal/logs/` ✅ |

---

## End-to-end flow

Run these in sequence to validate the full workflow from scratch:

1. `focal board setup` — configure board and repos (S1)
2. `focal board sync` — verify issues appear on board (BS1, BS2)
3. `focal board status` — confirm column counts (ST1)
4. `focal pm init owner/repo` — bootstrap a test repo (PI1, PI2)
5. Edit `docs/focal/plan.md` — add an epic and two stories
6. `focal pm adopt-plan owner/repo` — verify dry-run output (AP1)
7. `focal pm adopt-plan owner/repo --apply` — create issues, check epics.md rendered (AP2, AP3)
8. `focal pm epic-create owner/repo --title "Test Epic" --sp 8` — create an additional epic (EC2)
9. `focal pm story-create owner/repo --epic E2 --title "Test Story" --sp 3` — create a story (SC2)
7. `focal pm plan owner/repo --weeks 1 --start $(date +%Y-%m-%d) --team "YOU:8"` — plan iteration (PL1)
8. `focal pm status owner/repo` — check dashboard (PS1)
9. `focal cache refresh owner/repo` — verify cache is current (CR1)
10. Close the test story on GitHub, then `focal cache refresh owner/repo` — verify status updated (CR2)
11. `focal pm retro owner/repo --iteration I1 --goal-met --went-well "Smooth" --to-improve "Nothing"` — log retro (RE1)
12. `focal pm velocity owner/repo` — check velocity table shows I1 (V1)
13. `focal pm remove-repo owner/repo` — unregister repo (RR1)
14. `focal reset --yes` — clean up everything (R3)
15. `focal board setup` — reconfigure from scratch (S1 again)

---

## Reporting issues

Please include:
- The exact command you ran
- The full terminal output (including any error)
- Your OS and Python version: `python3 --version`
- Your `gh` CLI version: `gh --version`
- Whether this is a first run or subsequent run

File issues at: https://github.com/leninmehedy/focal/issues
