# Focal

Your personal command center for GitHub Issues — one Kanban board that stays in
sync with every project board you contribute to.

> **Built with AI. Best set up with AI.**
> Focal ships with [`AGENTS.md`](AGENTS.md) so any capable AI coding agent can
> clone, configure, and run it for you — no manual steps required.

## The problem

If you contribute to many GitHub repositories, each with its own project board,
planning your day looks like this: open repo A's board, find your cards, open
repo B's board, find your cards, repeat for every repo you're involved in.
By the time you've done the rounds, you've lost 20 minutes and you still don't
have a single prioritized view of what you're supposed to do today.

**Focal solves this.** Create one personal Kanban board — your command center —
and let Focal keep it in sync with every project board you contribute to. All
issues assigned to you flow in automatically. You prioritize and move cards in
one place. Status changes flow back out to the origin projects so your teammates
always see up-to-date progress. No more board-hopping.

## What it does

- **Pull** — Open issues assigned to you are automatically added to your personal board. New items inherit their status from the origin project.
- **Push** — When you move a card on your personal board, the status change is pushed to all origin projects the issue belongs to.
- **Stale** — When an issue is closed or unassigned from you, it is moved to your Done column automatically.
- **Conflict resolution** — Your personal board wins. If both sides change between syncs, your board's status is pushed to origin.

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

Once set up, your agent can manage Focal for you in plain language:

- *"Add hashgraph/solo-operator to my sync"*
- *"Why is issue #42 still showing as New?"*
- *"Reset and re-sync everything from scratch"*
- *"Show me warnings from the last sync"*
- *"The hourly sync stopped running — what's wrong?"*

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

## File reference

| File | Purpose |
|---|---|
| `focal.py` | CLI entry point — `python3 focal.py board sync` / `setup` |
| `focal/` | Python package — all sync and wizard logic |
| `sync.sh` / `setup.sh` | Thin shell wrappers (for launchd / cron) |
| `config.json` | Your personal config — **gitignored, never commit** |
| `config.example.json` | Template showing all config keys |
| `status_map.json` | Auto-generated status name mappings — **gitignored** |
| `AGENTS.md` | AI agent onboarding guide — read automatically by Claude Code, Codex, etc. |

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
