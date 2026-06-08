# Focal — AI Agent Guide

Focal is two tools in one:

1. **Board sync** — bidirectional sync between a personal GitHub Projects v2 Kanban
   board and origin repo project boards. All issues assigned to the user flow in
   automatically; status changes flow back out.

2. **PM CLI** — a full project management workflow: design docs, epics, stories,
   iteration planning, retrospectives, and live iteration status. Designed to be
   driven by an AI agent on behalf of a project manager.

---

## ⚠ Critical: use Focal commands, not `gh` directly

**When a user's project is managed with Focal, always use `focal` commands to create
and manage GitHub issues — never call `gh issue create`, `gh issue edit`, or any `gh`
project command directly.**

Focal maintains a local state cache (`focal-state.json`), keeps `docs/focal/epics.md`
in sync, links sub-issues, sets story point fields on the project board, and handles
epic/story ID assignment. Bypassing Focal with raw `gh` commands breaks all of that:
the cache goes stale, IDs conflict, sub-issue links are missing, and velocity tracking
becomes inaccurate.

| Task | ✅ Do this | ❌ Not this |
|---|---|---|
| Create an epic | `focal pm epic-create owner/repo --title "..." --sp N` | `gh issue create --label epic` |
| Create a story / bug fix | `focal pm story-create owner/repo --epic E0 --title "..."` | `gh issue create --label story` |
| Check project status | `focal pm status owner/repo` | `gh issue list` |
| Sync the board | `focal board sync` | `gh project item-list ...` |
| Refresh issue state | `focal cache refresh owner/repo` | `gh issue view ...` in a loop |

**Also: do not read or execute Focal's source code.** This file (`AGENTS.md`) is the
complete reference. You do not need to open `focal/`, inspect `focal.py`, or run
`python3 focal.py` directly. Just run the `focal` CLI commands documented here.

### Record this rule in the project you are working on

When you start working in a repo that uses Focal, write the following block into
`CLAUDE.md` (create it if it doesn't exist) so you remember the rule in every future
session without re-reading AGENTS.md:

```markdown
## Project management

This project uses [Focal](https://github.com/leninmehedy/focal) for issue tracking
and delivery management.

**Always use `focal` commands to create or update GitHub issues — never use `gh`
directly for issue or project management.**

| Task | Command |
|---|---|
| Create epic | `focal pm epic-create owner/repo --title "..." --sp N` |
| Create story or bug | `focal pm story-create owner/repo --epic EX --title "..."` |
| Unplanned work / bugs | `focal pm story-create owner/repo --epic E0 --title "..."` |
| Check iteration status | `focal pm status owner/repo` |
| Sync board | `focal board sync` |
| Refresh issue cache | `focal cache refresh owner/repo` |

E0 is the General Maintenance epic — always route bugs and unplanned work there.
Every task needs a GitHub issue before work begins.
```

Write this block once per project. Do not re-write it if it already exists.

---

## Integration modes

There are two ways to drive Focal as an agent:

| Mode | How | When to use |
|---|---|---|
| **CLI (AGENTS.md)** | Shell out to `focal` commands | Always available; no extra setup |
| **MCP skill** | Call `focal_*` tools directly as structured functions | When user has run `focal skill install` |

**Detecting which mode is available:** check whether `focal mcp serve` is in the
user's agent config (`~/.claude/settings.json` → `mcpServers.focal`). If present,
prefer MCP tools. Otherwise use CLI commands.

**MCP tool → CLI command mapping:**

| MCP tool | Equivalent CLI |
|---|---|
| `focal_board_setup` | `focal board setup` (non-interactive) |
| `focal_board_sync` | `focal board sync` |
| `focal_pm_init` | `focal pm init` |
| `focal_pm_adopt` | `focal pm adopt` |
| `focal_pm_adopt_plan` | `focal pm adopt-plan` |
| `focal_pm_triage` | `focal pm triage` |
| `focal_pm_epic_create` | `focal pm epic-create` |
| `focal_pm_story_create` | `focal pm story-create` |
| `focal_pm_plan` | `focal pm plan` |
| `focal_pm_whatif` | `focal pm what-if` |
| `focal_pm_status` | `focal pm status` |
| `focal_pm_retro` | `focal pm retro` |
| `focal_pm_design_list` | `focal pm design` |
| `focal_cache_refresh` | `focal cache refresh` |
| `focal_cache_status` | `focal cache status` |
| `focal_pm_solo_init` | `focal pm solo init` |
| `focal_pm_solo_status` | `focal pm solo status` |
| `focal_pm_solo_queue` | `focal pm solo queue` |
| `focal_pm_solo_start` | `focal pm solo start` |
| `focal_pm_solo_pr` | `focal pm solo pr` |
| `focal_pm_solo_ship` | `focal pm solo ship` |
| `focal_pm_solo_note` | `focal pm solo note` |

**Installing the MCP skill** (do this once during onboarding if the user wants it):

```bash
pip install focal[mcp]
focal skill install claude   # or: focal skill install cursor
```

---

## Repo contents

| File/Dir | Role |
|---|---|
| `focal.py` | CLI entry point — all commands live here |
| `focal/` | Python package — all logic |
| `focal/sync.py` | Board sync logic (`Syncer` class) |
| `focal/wizard.py` | Interactive setup wizard |
| `focal/gh.py` | `gh` CLI subprocess wrapper — all GitHub API calls |
| `focal/config.py` | `Config` dataclass, load/save `config.json` |
| `focal/pm/` | PM command modules |
| `focal/pm/pm_state.py` | Local state cache manager |
| `focal/pm/epic_cmd.py` | `focal pm epic-create` |
| `focal/pm/story_cmd.py` | `focal pm story-create` |
| `focal/pm/adopt_plan_cmd.py` | `focal pm adopt-plan` |
| `focal/pm/plan_doc_parser.py` | Parser for `docs/focal/plan.md` |
| `focal/pm/epics_renderer.py` | Re-renders `docs/focal/epics.md` from `focal-state.json` |
| `focal/pm/plan_cmd.py` | `focal pm plan` |
| `focal/pm/retro_cmd.py` | `focal pm retro` |
| `focal/pm/status_cmd.py` | `focal pm status` |
| `focal/pm/sync_state_cmd.py` | `focal cache refresh` |
| `focal/mcp_server.py` | MCP server — 13 tools exposing all PM and board commands |
| `focal/templates/` | Markdown templates bundled inside the package — copied to target repos by `focal pm init` |
| `docs/pm-guide.md` | Full PM workflow guide — read this for deep context |

---

## Full command surface

```
focal --version                      — print version
focal board sync                     — sync personal board with all origin boards
focal board setup                    — interactive wizard, writes ~/.focal/config.json
focal board setup \                  — non-interactive: --owner USER --repos owner/repo1,owner/repo2
  --owner USER --repos LIST \          --create-board (new) or --use-board --use-board-number N
  --create-board|--use-board-number N  --board-title TEXT  --assignee USER  --done-status TEXT

focal pm init <owner/repo>           — bootstrap repo with Focal PM structure
focal pm adopt <owner/repo>          — bootstrap state from existing issues (onboarding)
focal pm epic-create <owner/repo>    — create a GitHub epic issue
focal pm story-create <owner/repo>   — create a story linked to an epic
focal pm adopt-plan <owner/repo>     — bootstrap issues from docs/focal/plan.md (dry-run by default)
focal pm triage <owner/repo>         — list open issues not linked to any epic
focal pm plan <owner/repo>           — generate iteration-planning.md
focal pm retro <owner/repo>          — log completed iteration to retro-log.md
focal pm status [<owner/repo>]       — live iteration summary; omit repo to show all registered repos
focal pm design [--repo-root PATH]   — list design docs with status and epic linkage
focal pm what-if <owner/repo>        — dry-run simulation of plan under hypothetical scenarios
focal pm remove-repo <owner/repo>    — unregister a repo from PM tracking

focal pm solo init <owner/repo>      — solo mode: scaffold docs/focal/build-log.json + render docs/build-log.md
focal pm solo status [<owner/repo>]  — solo mode: terminal summary from build-log.json [--last N]
focal pm solo queue ISSUE BRANCH     — add item to Up next [--sp N] [--what TEXT]
focal pm solo start ISSUE            — move item Up next → In flight
focal pm solo pr ISSUE PR            — set PR number on an In flight row
focal pm solo ship ISSUE [PR]        — move item In flight → Shipped
focal pm solo note TEXT              — update Last action in build-log.json
focal pm solo render                 — re-render docs/build-log.md from build-log.json (idempotent)

focal cache refresh <owner/repo>     — re-fetch state for one repo from GitHub
focal cache refresh-all [--force]    — re-fetch all registered PM repos in one shot
focal cache status                   — show last sync time, counts, and auto-refresh config

focal mcp serve                      — start the MCP server (stdio transport)
focal skill install [claude|cursor]  — install Focal as an MCP skill in your agent

focal reset [--yes]                  — remove all config, state, and scheduler
```

All `focal pm` and `focal cache` commands accept `--repo-root PATH` to specify
a local clone of the target repo (default: current directory).

---

## Issue-first rule

**Every task — bug fix or new feature — must have a GitHub issue before any work begins.**

This is enforced by Focal's workflow: `focal pm story-create` always links a story to an
epic, and `focal pm init` creates a standing **E0 General Maintenance** epic to catch all
unplanned work.

### The General Maintenance epic (E0)

`focal pm init` automatically creates a permanent **E0 General Maintenance** epic on
GitHub. Use it as the parent for any work that arrives outside of iteration planning:

| Route to E0 | Route to a planned epic |
|---|---|
| Bug reports (user-filed or CI) | Work already scoped in a planned epic |
| Security patches, dependency upgrades | Any story created during iteration planning |
| Hotfixes mid-iteration | — |
| Housekeeping (CI, docs, tooling) | — |

**As an agent:** when asked to fix a bug or handle unplanned work, always create a
story under E0 first — never work without a ticket.

```bash
# Create a bug story under General Maintenance
focal pm story-create owner/repo --epic E0 --title "Fix login crash" --sp 3
```

User epics start at E1. E0 is reserved and never reassigned.

---

## Non-interactive flags (use these as an agent)

All PM commands support non-interactive flags so you can drive them without
answering prompts. Any flag you omit falls back to an interactive prompt for
the human user.

### `focal pm epic-create`

```bash
python3 focal.py pm epic-create <owner/repo> \
  --title "Epic title" \
  --description "One-line description" \
  --sp 21
```

### `focal pm story-create`

```bash
python3 focal.py pm story-create <owner/repo> \
  --epic E1 \              # epic ID from local state (E1, E2, …)
  --title "Story title" \
  --description "One-line description" \
  --sp 5
```

### `focal pm plan`

```bash
python3 focal.py pm plan <owner/repo> \
  --weeks 2 \
  --start 2026-05-19 \
  --team "alice:8,bob:6" \           # handle:SP/iter pairs, comma-separated
  --pto "alice:2026-06-27:2026-07-04" \  # repeatable; handle:from:to
  --goals "I1:Ship auth,I2:Close E2"     # label:goal text, comma-separated
```

`--pto` is repeatable: pass one `--pto` flag per person.

### `focal pm retro`

```bash
python3 focal.py pm retro <owner/repo> \
  --iteration I1 \
  --goal-met \                              # or --no-goal-met
  --went-well "No blockers this sprint" \   # repeatable
  --to-improve "Auth estimates were off" \  # repeatable
  --action "alice:Re-estimate carry-overs:2026-06-03" \  # repeatable; handle:text:due
  --notes "Good iteration overall"
```

`--went-well`, `--to-improve`, and `--action` are all repeatable — pass the flag
multiple times for multiple items.

### `focal pm adopt`

```bash
focal pm adopt <owner/repo> \
  --epic-label "epic,feature" \   # comma-separated labels identifying epics (default: epic)
  --story-label "story,task" \    # comma-separated labels identifying stories (default: story)
  --sp-field "Estimated SP" \     # optional; auto-detects common names if omitted
  --default-sp 3 \                # fallback SP for issues with no estimate
  --apply \                       # write focal-state.json (default: dry-run)
  --normalise \                   # re-format issues to Focal conventions (requires --apply)
  --prompt-missing                # prompt for SP on stories where none was found
```

**Always dry-run by default.** Pass `--apply` to write files. Use `--prompt-missing`
only in interactive sessions — skip it when running as an agent.

### `focal pm adopt-plan`

```bash
focal pm adopt-plan <owner/repo> \
  --from-plan docs/focal/plan.md \  # optional; defaults to docs/focal/plan.md
  --apply                           # create issues (default: dry-run)
```

Reads `docs/focal/plan.md` — a human/agent-authored file with epic headings and
story tables — creates GitHub issues for every item not yet tracked in
`focal-state.json`, links stories as sub-issues to their parent epics, and
re-renders `docs/focal/epics.md` from the updated state.

**Always dry-run by default.** Pass `--apply` to create issues. Idempotent —
re-running skips epics and stories already in state.

**Two-file model:**
- `docs/focal/plan.md` — human/agent-authored; focal **never writes** to this file
- `docs/focal/epics.md` — focal-owned; re-rendered from `focal-state.json` on every
  mutating command (`adopt-plan`, `epic-create`, `story-create`)

**Typical agent workflow:**

```
1. focal pm init owner/repo              # create scaffold including plan.md template
2. [agent writes docs/focal/plan.md]     # author epics, stories, release ladder
3. focal pm adopt-plan owner/repo        # dry-run — review what will be created
4. focal pm adopt-plan owner/repo --apply  # create issues, render epics.md
5. focal board sync                      # push new issues to board
```

### `focal pm triage`

```bash
focal pm triage <owner/repo> \
  --label bug        # filter by GitHub label (optional)
  --unassigned       # only show issues with no assignee (optional)
  --days 7           # only issues opened in the last N days (optional)
  --json             # JSON output instead of rich table (optional)
```

Lists open GitHub issues not tracked in `focal-state.json`. Use after ingesting a new repo or periodically to catch issues filed outside Focal's workflow. Route unplanned items to E0.

### `focal pm what-if`

```bash
focal pm what-if <owner/repo> \
  --pto "alice:2026-06-27:2026-07-04" \   # repeatable; HANDLE:FROM:TO
  --inject "Urgent fix:8" \               # repeatable; "TITLE:SP"
  --reestimate "1.3:13" \                 # repeatable; STORY_ID:SP
  --apply                                 # write updated iteration-planning.md (default: dry run)
```

All scenario flags are repeatable. Combine them freely — e.g. `--pto` + `--inject` in one command.

### `focal pm status`

Already non-interactive (display only). Use `--refresh` to pull latest GitHub state first.

### `focal pm solo` — solo mode

Use solo mode for repos where you want lightweight tracking without full iteration planning.
State lives in `docs/focal/build-log.json` (source of truth); `docs/build-log.md` is
rendered from it and is **focal-managed** — do not hand-edit it.

**Agent workflow for a task:**
```
focal pm solo queue #146 feat/146-no-plan-mode --sp 5 --what "focal pm solo commands"
focal pm solo start #146
focal pm solo note "PR open on feat/146-no-plan-mode"
focal pm solo pr #146 158
focal pm solo ship #146 158
focal pm solo note "Merged #158 — focal pm solo shipped"
```

`focal pm solo status` reads `build-log.json` directly — no GitHub calls, works offline.

### `focal cache refresh` / `refresh-all` / `status`

All non-interactive. `refresh-all` and `status` take no arguments — they operate
on all repos registered in `~/.focal/config.json` via `focal pm init`.

`refresh-all` respects two config guards (see below). Pass `--force` to bypass both.

---

## PM workflow — how to drive it as an agent

### Standard delivery cycle

```
1. focal pm init owner/repo              # one-time per repo (also registers it for refresh-all)
2. Write docs/focal/design/D001-*.md     # you or the human writes the design
3. focal pm epic-create  (per epic)      # read breakdown hint from design doc
4. focal pm story-create (per story)
5. focal pm plan                         # run once per release/quarter
6. focal pm status                       # check any time during delivery
7. focal pm retro                        # at the end of each iteration
8. focal cache refresh-all               # scheduled twice daily; run manually if stale
9. focal cache status                    # check sync age and issue counts across all repos
```

### Writing a design doc

When a human asks you to write or draft a design doc, always populate the
`## Breakdown hint` section before finishing. Use this exact format — the
parser is strict:

```
## Breakdown hint

Epic: <plain title, no quotes> (~N SP)
  - Story: <plain title> (N SP)
  - Story: <plain title> (N SP)
```

Rules:
- **One epic per design doc** (one `Epic:` line)
- Epic SP uses a tilde prefix: `(~N SP)` — this signals it's an estimate
- Story SP has no tilde: `(N SP)` — these are per-story point counts
- Titles are plain text — no backticks, bold, or markdown inside the line
- Each story line starts with exactly two spaces + `- Story:`
- The section ends at the next `##` heading or end of file

If any `## Impact` area is marked `Breaking`, add an explicit migration story
in the breakdown (e.g. `- Story: Write migration guide for X (2 SP)`).

### Reading the design doc for backlog structure

When a human says "create epics and stories from the design doc", do this:

1. Read the design doc at `docs/focal/design/D*.md`
2. Check `## Breakdown hint` is populated — if not, fill it in first (see above)
3. Run:
   ```
   focal pm epic-create <owner/repo> \
     --from-design docs/focal/design/<filename>.md \
     --repo-root <path>
   ```
   This creates the epic, all stories, links sub-issues, updates board SP,
   and advances the design doc status from `Planned → Active` — all in one command.
4. If the design doc is still `Draft` (not yet `Planned`), update its frontmatter
   `status` to `Planned` before running the command.

### Local state cache

Focal maintains `docs/focal/.cache/focal-state.json` in the target repo. This
cache is the source of truth for `plan`, `retro`, and `status`. GitHub is always
authoritative — the cache is a read-through for speed.

- `epic-create` and `story-create` write to the cache automatically
- `focal cache refresh <repo>` re-fetches one repo from GitHub
- `focal cache refresh-all` re-fetches all registered PM repos in one pass
- `focal pm plan --refresh` and `focal pm retro --refresh` trigger a refresh
  before running

Always run `focal cache refresh <repo>` if you suspect the cache is stale (e.g.
issues were closed or created directly on GitHub). Run `focal cache status` first
to see how stale each repo's cache actually is before deciding whether to refresh.

**Cache refresh scaling controls** (in `~/.focal/config.json`):

| Key | Default | Effect |
|---|---|---|
| `auto_cache_refresh` | `true` | Set to `false` to disable the launchd/cron scheduler; run manually with `--force` |
| `max_tracked_issues` | `500` | Repos with more tracked epics + stories than this are skipped by `refresh-all` |

If a repo is skipped due to the limit, refresh it individually:
```
focal cache refresh owner/repo --repo-root /path/to/repo
```
Or bypass all guards:
```
focal cache refresh-all --force
```

### Typical agent conversation patterns

**PM:** "Create epics and stories from our design doc"
→ Ensure `## Breakdown hint` is populated, then run `focal pm epic-create <repo> --from-design <path>`

**PM:** "Plan I1 — 2 weeks, starts Monday, me and @bob, bob has 6 SP"
→ `focal pm plan owner/repo --weeks 2 --start <next Monday> --team "pm_handle:8,bob:6"`

**PM:** "Log the retro for I1 — we hit our goal, good collab, estimates were off"
→ `focal pm retro owner/repo --iteration I1 --goal-met --went-well "Good collaboration" --to-improve "Estimation accuracy"`

**PM:** "What's our iteration status?"
→ `focal pm status owner/repo --refresh`

**PM:** "What slips if alice is out next week?" / "Model the impact of this PTO"
→ `focal pm what-if owner/repo --pto "alice:FROM:TO"` — dry run by default; add `--apply` to commit the updated plan

**PM:** "We need to squeeze in an urgent fix — what gets pushed?" / "Add X as high priority"
→ `focal pm what-if owner/repo --inject "Urgent fix:SP"` — shows which existing stories slip out

**PM:** "Story 1.3 is bigger than we thought — reforecast the plan"
→ `focal pm what-if owner/repo --reestimate "1.3:NEW_SP"`

**PM:** "We're onboarding Focal to an existing repo — bootstrap the state"
→ `focal pm adopt owner/repo --sp-field "Estimated SP"` (or omit `--sp-field` for auto-detect; add `--prompt-missing` if SP is absent from many issues)

---

## Onboarding a new user (board sync)

### Step 1 — Verify prerequisites

```bash
gh auth status        # must show "Logged in" with repo + project scopes
gh --version          # 2.x or later
python3 --version     # 3.10 or later
pipx --version        # or: pip3 install pipx
```

If the `project` scope is missing:
```bash
gh auth refresh -s project
```

### Step 2 — Install Focal and run setup wizard

Use the installer script (handles pipx, Python check, and focal-cli in one step):
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/leninmehedy/focal/main/install.sh)
```

Then run the wizard:
```bash
focal board setup
```

If working from a local clone of the repo instead:
```bash
pip3 install -e .
focal board setup
```

The wizard offers to **create a GitHub Projects v2 board automatically** — choose that
option unless the user already has a board they want to use. It pre-populates the
recommended Status columns and writes `~/.focal/config.json`.

### Step 4 — Verify sync

```bash
focal board sync
```

Final line should be:
```
[INFO ] Sync complete — added: N  inherited: N  pushed: 0  stale: 0
```

### Step 5 — Schedule recurring sync

**macOS (launchd):**
```bash
cp launchd/com.your-username.focal.plist ~/Library/LaunchAgents/com.YOUR_USERNAME.focal.plist
# Edit: replace YOUR_USERNAME and /path/to/focal
launchctl load ~/Library/LaunchAgents/com.YOUR_USERNAME.focal.plist
```

**Linux (cron):**
```bash
(crontab -l 2>/dev/null; echo "0 * * * * /path/to/focal/sync.sh") | crontab -
```

### Step 6 — Schedule PM cache refresh (optional but recommended)

If using the PM CLI, schedule a twice-daily cache refresh so `focal pm status`
stays accurate as issues are closed on GitHub throughout the day.

**macOS (launchd):**
```bash
cp launchd/com.your-username.focal-cache.plist ~/Library/LaunchAgents/com.YOUR_USERNAME.focal-cache.plist
# Edit: replace YOUR_USERNAME, /path/to/focal, and owner/repo
launchctl load ~/Library/LaunchAgents/com.YOUR_USERNAME.focal-cache.plist
```

**Linux (cron):**
```bash
(crontab -l 2>/dev/null; echo "0 8,14 * * * python3 /path/to/focal/focal.py cache refresh-all >> ~/.focal/logs/cache-refresh.log 2>&1") | crontab -
```

`refresh-all` reads all registered PM repos from `~/.focal/config.json` — no repo
arguments needed. Repos are registered automatically when `focal pm init` is run.

---

## Common tasks

### Add or remove repos from board sync

Edit `~/.focal/config.json`:
```json
"repos": ["owner/repo-one", "owner/repo-two"]
```

Or re-run `focal board setup` — it detects the existing config and offers **Add repos**, **Edit repo list**, or **Full reconfigure**.

### Remove a PM-tracked repo

```bash
focal pm remove-repo owner/repo
```

This removes the entry from `pm_repos` in `~/.focal/config.json` so `refresh-all` no longer processes it. It does not delete any local files.

### Reset sync state

```bash
rm ~/.focal/state.json && python3 focal.py board sync
```

### Check logs

```bash
tail -f ~/.focal/logs/$(date '+%Y-%m-%d').log
grep 'WARN' ~/.focal/logs/*.log
```

---

## Architecture notes

- **`focal/gh.py`** — all GitHub API calls via `gh` CLI subprocess. GraphQL for
  project mutations; REST for issue listing. No raw API token needed.
- **`focal/pm/pm_state.py`** — local state cache at `docs/focal/.cache/focal-state.json`
  in the target repo. Stamped with `last_synced` ISO-8601 timestamp on every write.
- **State schema:** `{repo, last_synced, epics: [{id, title, issue_number, sp, status,
  stories: [{id, title, issue_number, sp, assignee, status, project_status}]}],
  iterations: [{label, start, end, capacity_sp, story_ids, goal}]}`
- **Conflict resolution (board sync)** — personal board wins. If both sides change
  between syncs, the personal board status is pushed to origin.
- **Status matching** is emoji-normalized: `🏗 In progress` and `In progress` match.
- Python 3.10+ required (`list[str]`, `dict[str, str]` type hints without `typing`).

## Key config fields (`~/.focal/config.json`)

| Field | Default | Description |
|---|---|---|
| `board_owner` | — | GitHub username who owns the personal board |
| `board_number` | — | Project number from the board URL |
| `assignee` | — | GitHub username to filter assigned issues |
| `status_field_id` | — | Node ID of the Status single-select field on the personal board |
| `done_status` | `✅ Done` | Exact name of the Done option |
| `repos` | `[]` | Array of `owner/repo` strings to sync |
| `pm_repos` | `[]` | Array of `{repo, repo_root}` objects registered by `focal pm init` |
| `auto_cache_refresh` | `true` | Set to `false` to disable launchd/cron scheduler |
| `max_tracked_issues` | `500` | Skip repos with more tracked epics + stories than this in `refresh-all` |
| `state_file` | `~/.focal/state.json` | Board sync state |
| `log_dir` | `~/.focal/logs` | Directory for daily log files |

## Things to be careful about

- `~/.focal/config.json` and `~/.focal/status_map.json` are gitignored — never commit them.
- `gh` token needs `project` scope. Without it, project queries silently return empty.
- `gh project item-add` is idempotent — safe to call multiple times for the same URL.
- The local state cache (`docs/focal/.cache/focal-state.json`) is safe to commit —
  it contains no secrets, only metadata mirroring GitHub.
- Never edit `.focal-state.json` manually — use `focal cache refresh` to update it.

---

## Contributing — rules for agents and human contributors

### Every PR must update `docs/testing-guide.md`

`docs/testing-guide.md` is the beta tester test plan. It must stay in sync with the code:

- **New command** → add a new section with a numbered test table (match the existing format)
- **Changed behavior or flags** → update the affected test rows
- **Removed command** → remove its section

Include the `testing-guide.md` change in the **same PR** as the feature or fix — never in a separate PR.

### Commit message format

Use [Conventional Commits](https://www.conventionalcommits.org/) — they drive semantic-release versioning:

| Prefix | Bump | Use for |
|---|---|---|
| `feat:` | minor | New commands, new flags, new behavior |
| `fix:` | patch | Bug fixes, error message improvements |
| `docs:` | none | README, AGENTS.md, pm-guide, testing-guide |
| `chore:` | none | CI, deps, tooling, merge conflict resolution |
| `perf:` | patch | Performance improvements |
| `refactor:` | patch | Internal restructuring, no behavior change |

### Before committing

Always run ruff on files you touched:

```bash
pip3 install ruff -q
ruff check --fix <files>
ruff format <files>
```

CI enforces both — a ruff failure will block the PR.

### Branch and PR rules

- Branch from `main`: `git checkout -b feat/my-feature`
- PR target is always `main` — direct push to `main` is blocked by branch protection
- Keep PRs focused: one feature or fix per PR
- PR title should match the commit prefix: `feat: ...`, `fix: ...`, etc.

### What not to do

- Do not add comments that describe *what* code does — well-named identifiers do that
- Do not add error handling for scenarios that cannot happen
- Do not create new files when editing an existing one is sufficient
- Do not add backwards-compatibility shims for code that has no external callers
