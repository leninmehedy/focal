# Focal

Your personal command center for GitHub — one Kanban board that stays in sync
with every project you contribute to, plus a full project management CLI for
running delivery end-to-end without leaving the terminal.

> **Built with AI. Best used with AI.**
> Focal ships with [`AGENTS.md`](AGENTS.md) so any capable AI agent (Claude Code,
> Cursor, Codex) can set it up, run PM commands, and manage your backlog on your
> behalf — no manual steps required.

## The problem

If you contribute to many GitHub repositories, each with its own project board,
planning your day means opening every repo board one by one. By the time you've
done the rounds, you've lost 20 minutes and still don't have a single prioritized
view of your work.

And when it comes to planning a release — creating epics, estimating stories,
building an iteration schedule, logging retros — you're either doing it in Jira
(context switch) or in your head (no record).

**Focal solves both.** One personal Kanban board that syncs everywhere, plus a
PM CLI that manages your entire delivery lifecycle in GitHub and markdown — no
external tools, no context switching.

## What it does

### Board sync
- **Pull** — Open issues assigned to you are automatically added to your personal board. New items inherit their status from the origin project.
- **Push** — When you move a card on your personal board, the status change is pushed to all origin projects the issue belongs to.
- **Stale** — When an issue is closed or unassigned from you, it is moved to your Done column automatically.
- **Conflict resolution** — Your personal board wins. If both sides change between syncs, your board's status is pushed to origin.

### PM CLI
- **`focal pm init`** — bootstrap any repo with epics tracker, iteration planning doc, retro log, and design doc templates
- **`focal pm epic-create`** / **`story-create`** — create GitHub issues, link sub-issues, set SP on the board — all in one command
- **`focal pm plan`** — build an iteration schedule from your backlog: team capacity, PTO reduction, greedy SP assignment, risk identification
- **`focal pm retro`** — close out an iteration: delivered vs carry-over, slip reason codes, goal met?, what went well, action items
- **`focal pm status`** — live terminal dashboard: progress bar, blocked stories, projected delivery
- **`focal cache refresh`** — pull latest GitHub state into the local cache anytime

---

## Set up with an AI agent (recommended)

Focal is AI-native. It ships with [`AGENTS.md`](AGENTS.md) — a detailed guide
that AI coding agents read automatically on startup. This means your agent
already knows how to install, configure, and operate Focal before you say a word.

**Supported agents:** Claude Code, OpenAI Codex, Cursor, or any agent that
reads `AGENTS.md` from the project root and can run shell commands.

### Option 1 — Let your agent do everything

Open your AI agent and paste a single prompt:

```
Set up Focal from https://github.com/leninmehedy/focal
```

The agent will:
1. Clone the repo
2. Check prerequisites (`gh` CLI, Python 3)
3. Run the interactive setup wizard (asking you only for your board URL and repos)
4. Verify the first sync works
5. Install the hourly scheduler (launchd on macOS, cron on Linux)

### Option 2 — Clone first, then hand off to your agent

```bash
git clone https://github.com/leninmehedy/focal.git
cd focal
claude        # Claude Code CLI
# or: open in VS Code / Cursor with the AI extension active
```

Then just say:
> *"Set up Focal for me"*

### Ongoing use — things you can ask your agent

Once set up, your agent can manage both board sync and PM workflows in plain language:

**Board sync**
- *"Add hashgraph/solo-operator to my sync"*
- *"Why is issue #42 still showing as New?"*
- *"Show me warnings from the last sync"*

**Project management**
- *"Read our design doc and create the epics and stories"*
- *"Plan I1 — 2-week sprint, me and @bob at 8 SP each, starting Monday"*
- *"What's our iteration status?"*
- *"Log the I1 retro — we hit our goal, no blockers, estimates were a bit off"*

---

## Manual setup

Prefer to do it yourself? No problem.

### Prerequisites

- [GitHub CLI (`gh`)](https://cli.github.com) — authenticated with `repo` and `project` scopes
- Python 3.10+
- A personal [GitHub Projects v2](https://docs.github.com/en/issues/planning-and-tracking-with-projects) board with a **Status** single-select field

### Install and configure

```bash
git clone https://github.com/leninmehedy/focal.git
cd focal
pip3 install -r requirements.txt
python3 focal.py board setup
```

The setup wizard guides you through everything interactively and generates
`config.json`. Then run a sync manually to verify:

```bash
python3 focal.py board sync
```

### Selecting repos

During setup you can choose one of three modes:

| Mode | Description |
|---|---|
| **Manual list** | Type repos one by one (`owner/repo`) |
| **Interactive select** | Browse and pick from your accessible repos |
| **Full scan** | Scans ALL repos you have access to (slow — may take minutes) |

You can edit the `repos` array in `config.json` at any time to add or remove repos.

### Status column alignment

The setup wizard inspects the Status columns of every origin project and compares
them to your personal board. It will:

1. **Report** any mismatches (missing options, different names)
2. **Generate `status_map.json`** to translate incompatible status names at sync time

Recommended personal board Status columns:

```
🆕 New  ·  📋 Backlog  ·  🔖 Ready  ·  🏗 In progress  ·  ✋ Blocked  ·  👀 In review  ·  ✅ Done
```

Status matching is emoji-normalized — `🏗 In progress` and `In progress` are
treated as the same status, so minor cosmetic differences don't break the sync.

### Schedule recurring sync

**macOS (launchd — recommended):**

```bash
cp launchd/com.your-username.focal.plist ~/Library/LaunchAgents/com.YOUR_USERNAME.focal.plist
# Edit the plist: replace YOUR_USERNAME and /path/to/focal
launchctl load ~/Library/LaunchAgents/com.YOUR_USERNAME.focal.plist
```

Useful commands:
```bash
launchctl list | grep focal                    # check status and last exit code
launchctl start com.YOUR_USERNAME.focal        # trigger an immediate run
launchctl unload ~/Library/LaunchAgents/...   # disable
```

**Linux / alternative (cron):**
```bash
(crontab -l 2>/dev/null; echo "0 * * * * /path/to/focal/sync.sh") | crontab -
```

### Schedule PM cache refresh

The PM state cache (`docs/focal/.cache/focal-state.json`) drifts when issues are
closed or updated on GitHub outside Focal. A twice-daily `refresh-all` keeps
`focal pm status` accurate without manual runs.

**macOS (launchd):**

```bash
cp launchd/com.your-username.focal-cache.plist ~/Library/LaunchAgents/com.YOUR_USERNAME.focal-cache.plist
# Edit the plist: replace YOUR_USERNAME and /path/to/focal
launchctl load ~/Library/LaunchAgents/com.YOUR_USERNAME.focal-cache.plist
```

The template runs at **08:00 and 14:00** daily. Edit `StartCalendarInterval` to adjust.

**Linux / alternative (cron):**
```bash
(crontab -l 2>/dev/null; echo "0 8,14 * * * python3 /path/to/focal/focal.py cache refresh-all >> ~/.focal/logs/cache-refresh.log 2>&1") | crontab -
```

`refresh-all` reads `pm_repos` from `~/.focal/config.json` — no repo arguments needed.
Run `focal pm init owner/repo` for each repo to register it automatically.

**Scaling controls** — add these keys to `~/.focal/config.json` as needed:

```json
"auto_cache_refresh": false,   // disable the scheduler; refresh manually with --force
"max_tracked_issues": 500      // skip repos with more tracked epics+stories than this
```

Check cache health across all repos at any time:
```bash
python3 focal.py cache status
```

---

## Logging

Logs are written to `~/.focal/logs/YYYY-MM-DD.log` (one file per day, naturally
self-rotating). Override via `log_dir` in `config.json`.

```
[2026-05-15 17:09:10] [INFO ] Board: #3 (PVT_kwHOAAxhrc4BXwuQ)
[2026-05-15 17:09:14] [INFO ] Adding: https://github.com/some-org/some-repo/issues/42
[2026-05-15 17:09:47] [WARNING] 'In Progress' not found in "some-org's project" — skipping
[2026-05-15 17:31:22] [INFO ] Sync complete — added: 3  inherited: 3  pushed: 1  stale: 0
```

Every run ends with a summary line showing counts: added, inherited, pushed, stale.

```bash
tail -f ~/.focal/logs/$(date '+%Y-%m-%d').log   # follow live
grep 'WARN' ~/.focal/logs/*.log                  # see all warnings
```

---

## PM CLI — manage delivery end-to-end

The PM commands work on any target repo, not just Focal itself. Point them at
whatever repo you're managing.

### Quick start

```bash
# Bootstrap a repo
python3 focal.py pm init owner/repo --repo-root /path/to/repo

# Create backlog
python3 focal.py pm epic-create owner/repo --title "OAuth support" --sp 21
python3 focal.py pm story-create owner/repo --epic E1 --title "GitHub OAuth flow" --sp 5

# Plan iterations
python3 focal.py pm plan owner/repo --weeks 2 --team "alice:8,bob:6"

# During delivery
python3 focal.py pm status owner/repo

# End of iteration
python3 focal.py pm retro owner/repo --iteration I1 --goal-met

# Check cache health across all registered repos
python3 focal.py cache status

# Refresh all registered repos (or one specific repo)
python3 focal.py cache refresh-all
python3 focal.py cache refresh owner/repo
```

All commands work interactively (prompts) if you omit the flags, or fully
non-interactively (flags only) for scripting and AI agent use.

### AI-native workflow

A project manager can describe work to Claude Code and Claude will run the
focal commands:

> *"Read our design doc and create the epics and stories"*
> *"Plan I1 for me and @bob, 2-week sprint starting Monday"*
> *"Log the I1 retro — we hit our goal, estimates were a bit off"*

Claude reads [`AGENTS.md`](AGENTS.md) automatically, so it already knows the
full command surface and non-interactive flags before you ask.

For the full PM workflow — design docs, breakdown hints, Impact tables, and the
delivery cycle — see [`docs/pm-guide.md`](docs/pm-guide.md).

---

## File reference

| File | Purpose |
|---|---|
| `focal.py` | CLI entry point — all commands |
| `focal/` | Python package — sync, wizard, PM modules |
| `focal/pm/` | PM command modules (epic, story, plan, retro, status) |
| `templates/` | Markdown templates copied by `focal pm init` |
| `docs/pm-guide.md` | Full PM workflow guide |
| `sync.sh` / `setup.sh` | Thin shell wrappers (for launchd / cron) |
| `launchd/com.your-username.focal.plist` | macOS scheduler template — board sync (hourly) |
| `launchd/com.your-username.focal-cache.plist` | macOS scheduler template — PM cache refresh (twice daily) |
| `config.json` | Your personal config — **gitignored, never commit** |
| `config.example.json` | Template showing all config keys |
| `status_map.json` | Auto-generated status name mappings — **gitignored** |
| `AGENTS.md` | AI agent guide — read automatically by Claude Code, Codex, etc. |

## State file

Sync state is stored at `~/.focal/state.json` (configurable in `config.json`).
Delete it to reset the baseline — the next sync will re-inherit all statuses
from origin.

## Limitations

- Sync is poll-based (no webhooks). GitHub does not emit events for personal
  project board card moves. Frequency is controlled by your scheduler interval.
- Status pushes to origin are best-effort: if an origin project doesn't have a
  matching status option, that project is skipped with a warning in the log.
- The `gh` token must have `project` scope for both your personal board and any
  origin org projects you want to write to.
