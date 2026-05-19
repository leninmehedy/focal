# Focal Beta Testing Guide

This guide covers every command in Focal. For each command there is a list of test cases — what to run, what to look for, and what constitutes a pass or fail.

**Prerequisites before starting:**
- `gh` CLI authenticated: `gh auth status` shows `Logged in` with `repo` and `project` scopes
- Python 3.10+: `python3 --version`
- A personal [GitHub Projects v2](https://docs.github.com/en/issues/planning-and-tracking-with-projects) board with a **Status** single-select field
- At least one GitHub repo with open issues assigned to you

**Notation:**
- ✅ Expected pass — the test should succeed with this output
- ❌ Expected failure — the command should fail gracefully with a clear error, not a traceback

---

## Setup

### `focal board setup`

The interactive wizard that creates `~/.focal/config.json`.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| S1 | Fresh setup | `python3 focal.py board setup` with no existing config | Wizard prompts for board URL, GitHub username, Done column name, repos to sync. Creates `~/.focal/config.json` ✅ |
| S2 | Config file location | After S1, `cat ~/.focal/config.json` | File exists at `~/.focal/config.json` (not in the focal repo directory) ✅ |
| S3 | Re-run wizard — add repos | Re-run `python3 focal.py board setup` when config already exists | Offers 3 choices: **Add repos**, **Edit repo list**, **Full reconfigure**. Choosing "Add repos" appends to the `repos` array without touching other settings ✅ |
| S4 | Re-run wizard — full reconfigure | Choose "Full reconfigure" in S3 | Overwrites config from scratch ✅ |
| S5 | Cancel re-run | Choose "Cancel" when offered options | Exits cleanly with no changes ✅ |
| S6 | Status map created | After setup with mismatched status columns | `~/.focal/status_map.json` is created with translation mappings ✅ |

---

## Board sync

### `focal board sync`

Bidirectional sync between your personal board and origin repo project boards.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| BS1 | Basic sync | `python3 focal.py board sync` | Runs without error. Last log line: `Sync complete — added: N  inherited: N  pushed: N  stale: N` ✅ |
| BS2 | Issues appear on board | After BS1, open `https://github.com/users/YOUR_USERNAME/projects/N` | All open issues assigned to you across configured repos are visible on the board ✅ |
| BS3 | Incremental sync | Run sync twice in a row | Second run output includes `(incremental)` and is faster; issues unchanged since first run are not re-fetched ✅ |
| BS4 | Status inheritance | Add a new issue (assigned to you) to a repo that has its own project board | After sync, new issue appears on personal board with status matching the origin project ✅ |
| BS5 | Push to origin | Move a card on your personal board, then sync | The status change is pushed to origin project boards the issue belongs to ✅ |
| BS6 | Stale handling | Close or unassign an issue that is on your board, then sync | Issue is moved to Done column on personal board ✅ |
| BS7 | No config | Delete `~/.focal/config.json`, then `python3 focal.py board sync` | Clear error: `Focal is not configured. Run focal board setup ...` — no traceback ❌ |
| BS8 | Desktop notification (macOS) | After sync completes | macOS notification appears: "Focal sync complete" with counts ✅ |
| BS9 | Disable notification | Set `"notifications": false` in `~/.focal/config.json`, sync again | No notification fires ✅ |
| BS10 | Log file created | After sync | `~/.focal/logs/YYYY-MM-DD.log` exists and contains sync output ✅ |

### `focal board status`

Live board summary — no sync, just reads current state.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| ST1 | Basic status | `python3 focal.py board status` | Rich table with one row per Status column showing issue counts. Total row at bottom ✅ |
| ST2 | Blocked items shown | Have at least one issue in a "Blocked" status column | "Blocked (N)" section appears below the table with issue refs and URLs ✅ |
| ST3 | Recently added shown | Have issues added to board in last 7 days | "Recently added" section shows those issues with status label ✅ |
| ST4 | No config | Delete `~/.focal/config.json`, then run | Clear error: `Focal is not configured.` — no traceback ❌ |
| ST5 | Empty board | Run on a newly created board with no items | Table shows all columns with 0 counts, no blocked/recent sections ✅ |

---

## Reset

### `focal reset`

Removes all Focal config, state, logs, and launchd/cron plists.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| R1 | Interactive prompt | `python3 focal.py reset` | Lists files to delete and asks for confirmation ✅ |
| R2 | Cancel | Answer `n` at prompt | Nothing is deleted ✅ |
| R3 | Confirm deletion | Answer `y` at prompt | `~/.focal/config.json`, `~/.focal/status_map.json`, `~/.focal/state.json`, `~/.focal/logs/` are removed ✅ |
| R4 | Skip prompt | `python3 focal.py reset --yes` | Deletes immediately without confirmation prompt ✅ |
| R5 | launchd cleanup (macOS) | With a loaded focal plist, run `focal reset --yes` | `launchctl unload` is called on matching plists and plist files are deleted ✅ |
| R6 | Missing files | Run reset when some files are already missing | Completes cleanly — skips missing files silently ✅ |
| R7 | Post-reset message | After reset | Prints: `✔ Reset complete. Run 'focal board setup' to reconfigure.` ✅ |

---

## Project management

### `focal pm init`

Bootstraps a repo with Focal PM structure.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| PI1 | Basic init | `python3 focal.py pm init owner/repo --repo-root /path/to/repo` | Creates `.github/ISSUE_TEMPLATE/epic.md`, `.github/ISSUE_TEMPLATE/story.md`, `docs/focal/epics.md`, `docs/focal/iteration-planning.md`, `docs/focal/retro-log.md`, `docs/focal/design/`. Labels `epic` and `story` created on GitHub ✅ |
| PI2 | Auto-registers repo | After PI1, `cat ~/.focal/config.json` | `pm_repos` array contains `{"repo": "owner/repo", "repo_root": "/path/to/repo"}` ✅ |
| PI3 | Safe to re-run | Run init again on same repo | Existing files are not overwritten. Re-run exits cleanly ✅ |
| PI4 | No board setup | Run without `~/.focal/config.json` | Clear error asking to run `focal board setup` first ❌ |
| PI5 | Wrong repo | `python3 focal.py pm init nonexistent/repo` | `gh` error surfaced clearly — no traceback ❌ |

### `focal pm epic-create`

Creates a GitHub epic issue.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| EC1 | Interactive | `python3 focal.py pm epic-create owner/repo` | Prompts for title, description, SP. Creates a GitHub issue with label `epic`. Adds to personal board with SP set. Appends to local state cache ✅ |
| EC2 | Non-interactive | `python3 focal.py pm epic-create owner/repo --title "My Epic" --description "Desc" --sp 13` | Creates issue without any prompts. Prints epic ID (E1, E2, …) and GitHub URL ✅ |
| EC3 | ID increments | Create two epics | First gets `E1`, second gets `E2` ✅ |
| EC4 | State cache updated | After EC2, `cat docs/focal/.cache/focal-state.json` in the target repo | Epic entry present with correct `issue_number`, `sp`, `status: "open"` ✅ |
| EC5 | No board setup | Run without config | Clear error ❌ |

### `focal pm story-create`

Creates a story issue linked to an epic.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| SC1 | Interactive | `python3 focal.py pm story-create owner/repo` | Prompts for epic (shows list), title, description, SP ✅ |
| SC2 | Non-interactive | `python3 focal.py pm story-create owner/repo --epic E1 --title "My Story" --description "Desc" --sp 5` | Creates issue with label `story`, linked as sub-issue of the epic. Story ID is `1.1`, `1.2`, etc. ✅ |
| SC3 | Sub-issue link | After SC2, open epic on GitHub | Story appears in the sub-issues list of the epic ✅ |
| SC4 | SP on board | After SC2, open personal board | Story card has SP value set in the Estimate/SP field ✅ |
| SC5 | Wrong epic ID | `--epic E99` on a repo with no E99 | Clear error: epic not found — no traceback ❌ |

### `focal pm plan`

Generates `docs/focal/iteration-planning.md` from the local state cache.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| PL1 | Basic plan | `python3 focal.py pm plan owner/repo --weeks 2 --start 2026-06-02 --team "alice:8,bob:6"` | Creates `docs/focal/iteration-planning.md` with iteration schedule, capacity, SP allocation, risk section ✅ |
| PL2 | PTO reduction | `--pto "alice:2026-06-09:2026-06-13"` | Alice's capacity reduced proportionally for that iteration ✅ |
| PL3 | Goal labels | `--goals "I1:Ship auth,I2:Close E2"` | Each iteration in the doc has its goal label ✅ |
| PL4 | Interactive | Run without flags | Prompts for each input ✅ |
| PL5 | With refresh | `--refresh` flag | Fetches latest state from GitHub before planning ✅ |
| PL6 | Empty backlog | Run with no epics/stories in cache | Warns that backlog is empty, exits cleanly ✅ |

### `focal pm retro`

Closes out an iteration and appends to `docs/focal/retro-log.md`.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| RE1 | Basic retro | `python3 focal.py pm retro owner/repo --iteration I1 --goal-met --went-well "Good collab" --to-improve "Estimates" --notes "Good sprint"` | Appends iteration block to `docs/focal/retro-log.md` with delivered vs carry-over, velocity metrics ✅ |
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
| PS1 | Basic status | `python3 focal.py pm status owner/repo` | Shows progress bar, SP delivered vs planned, list of stories with assignee and status ✅ |
| PS2 | With refresh | `python3 focal.py pm status owner/repo --refresh` | Fetches latest GitHub state before displaying ✅ |
| PS3 | Blocked stories | Have a story in "Blocked" status | Blocked stories highlighted separately ✅ |
| PS4 | No iterations planned | Run before `focal pm plan` | Friendly message: no active iteration found ✅ |
| PS5 | Stale cache warning | Cache last synced > 24h ago (check `last_synced` in state file) | Warning shown that cache may be stale ✅ |

### `focal pm velocity`

Historical velocity table from `docs/focal/retro-log.md`.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| V1 | Basic velocity | `python3 focal.py pm velocity owner/repo` (after at least one retro) | Rich table with one row per iteration: label, goal met, capacity SP, planned SP, delivered SP, carry-over SP, efficiency % ✅ |
| V2 | Average row | After 2+ retros | Bottom row shows averages across all iterations ✅ |
| V3 | Footer totals | | One-line footer: `N iterations · X SP delivered · avg carry-over: Y SP/iter` ✅ |
| V4 | No retro-log.md | Run before any retro | Friendly message: no retro data found — no traceback ✅ |
| V5 | Empty retro-log.md | File exists but has no iteration blocks | Same friendly message as V4 ✅ |

### `focal pm remove-repo`

Unregisters a repo from PM tracking.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| RR1 | Remove registered repo | `python3 focal.py pm remove-repo owner/repo` | Entry removed from `pm_repos` in `~/.focal/config.json`. Confirmation printed ✅ |
| RR2 | Remove unregistered repo | Run on a repo not in `pm_repos` | Clear message: repo not found in pm_repos — exits cleanly ✅ |
| RR3 | Local files untouched | After RR1, check the repo directory | `docs/focal/` and state cache are not deleted ✅ |
| RR4 | No longer in refresh-all | After RR1, `focal cache refresh-all` | Removed repo is not processed ✅ |

---

## Cache

### `focal cache refresh`

Re-fetches state for one repo from GitHub.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| CR1 | Basic refresh | `python3 focal.py cache refresh owner/repo --repo-root /path/to/repo` | Fetches epic/story state from GitHub. Prints count of synced epics/stories. Updates `last_synced` in state file ✅ |
| CR2 | Reflects closed issues | Close an issue on GitHub, then refresh | Issue `status` in cache changes from `open` to `closed` ✅ |
| CR3 | Project status updated | Move a story card on GitHub project board, then refresh | `project_status` field updated in cache ✅ |
| CR4 | No cache file | Run on repo that hasn't had `focal pm init` | Graceful error: no state cache found ❌ |

### `focal cache refresh-all`

Re-fetches all registered PM repos.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| CA1 | Basic refresh-all | `python3 focal.py cache refresh-all` | Processes all repos in `pm_repos`. Summary line per repo ✅ |
| CA2 | Force flag | `python3 focal.py cache refresh-all --force` | Bypasses `auto_cache_refresh` and `max_tracked_issues` guards ✅ |
| CA3 | Over limit skipped | Set `max_tracked_issues: 5` in config, have a repo with more epics+stories | That repo is skipped with a warning ✅ |
| CA4 | Disabled scheduler | Set `auto_cache_refresh: false` | `refresh-all` without `--force` skips all repos with message ✅ |
| CA5 | No pm_repos | Run with empty `pm_repos` | Friendly message: no repos registered — run `focal pm init` first ✅ |

### `focal cache status`

Shows cache health across all registered repos.

| # | Test | How to run | Expected result |
|---|------|-----------|-----------------|
| CS1 | Basic status | `python3 focal.py cache status` | Rich table: repo, last synced (relative time), epic count, story count, total vs limit, health indicator ✅ |
| CS2 | Stale indicator | Repo not refreshed in 24+ hours | Row shows warning indicator (⚠) ✅ |
| CS3 | Over-limit indicator | Repo with tracked issues > `max_tracked_issues` | Row shows warning indicator ✅ |
| CS4 | No pm_repos | Empty `pm_repos` | Friendly message: no repos registered ✅ |

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
5. `focal pm epic-create owner/repo --title "Test Epic" --sp 8` — create an epic (EC2)
6. `focal pm story-create owner/repo --epic E1 --title "Test Story" --sp 3` — create a story (SC2)
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
