# Focal

Your personal command center for GitHub Issues — one Kanban board that stays in
sync with every project board you contribute to.

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

## Prerequisites

- [GitHub CLI (`gh`)](https://cli.github.com) — authenticated with `repo` and `project` scopes
- Python 3 (standard library only)
- A personal [GitHub Projects v2](https://docs.github.com/en/issues/planning-and-tracking-with-projects) board with a **Status** single-select field

## Quick start

```bash
git clone https://github.com/leninmehedy/focal.git
cd focal
pip3 install -r requirements.txt
python3 focal.py setup
```

The setup wizard guides you through everything interactively and generates
`config.json`. Then run a sync manually to verify:

```bash
python3 focal.py sync
```

## Selecting repos

During setup you can choose one of three modes:

| Mode | Description |
|---|---|
| **Manual list** | Type repos one by one (`owner/repo`) |
| **Interactive select** | Browse and pick from your accessible repos |
| **Full scan** | Scans ALL repos you have access to (slow — may take minutes) |

You can edit the `repos` array in `config.json` at any time to add or remove repos.

## Status column alignment

`setup.sh` inspects the Status columns of every origin project and compares them
to your personal board. It will:

1. **Report** any mismatches (missing options, different names)
2. **Offer to fix** them by adding missing options to origin projects
3. **Generate `status_map.json`** as a fallback for projects it cannot fix
   (e.g. projects you don't own) — this maps origin status names to your
   personal board names at sync time

Recommended personal board Status columns:

```
🆕 New  ·  📋 Backlog  ·  🔖 Ready  ·  🏗 In progress  ·  ✋ Blocked  ·  👀 In review  ·  ✅ Done
```

Status matching is emoji-normalized — `🏗 In progress` and `In progress` are
treated as the same status, so minor cosmetic differences don't break the sync.

## Logging

Logs are written to `~/.focal/logs/YYYY-MM-DD.log` (one file per day, naturally
self-rotating). Override the directory via `log_dir` in `config.json`. When
running interactively, logs are also printed to stdout.

**Format:**
```
[2026-05-15 17:09:10] [INFO ] Board: #3 (PVT_kwHOAAxhrc4BXwuQ)
[2026-05-15 17:09:14] [INFO ] Adding: https://github.com/some-org/some-repo/issues/42
[2026-05-15 17:09:47] [WARN ] 'In Progress' not found in "some-org's project" — skipping
[2026-05-15 17:31:22] [INFO ] Sync complete — added: 3  inherited: 3  pushed: 1  stale: 0  log: /...
```

**Severity levels:** `[INFO ]`, `[WARN ]`, `[ERROR]`

**Summary line** — every run ends with a count of: issues added, statuses
inherited from origin, statuses pushed to origin, and stale items moved to Done.

View today's log:
```bash
tail -f ~/.focal/logs/$(date '+%Y-%m-%d').log
```

Grep for warnings:
```bash
grep '\[WARN\]' ~/.focal/logs/*.log
```

## Recurring sync

### macOS (recommended) — launchd

launchd is more reliable than cron on macOS: it survives sleep/wake cycles and
starts automatically on login.

A ready-to-use plist is provided. Install it with:

```bash
cp launchd/com.your-username.focal.plist ~/Library/LaunchAgents/
# Edit the plist to set your username and script path, then:
launchctl load ~/Library/LaunchAgents/com.your-username.focal.plist
```

Useful commands:

```bash
# Check status (shows last exit code)
launchctl list | grep focal

# Trigger a manual run immediately
launchctl start com.your-username.focal

# Disable
launchctl unload ~/Library/LaunchAgents/com.your-username.focal.plist
```

### Linux / alternative — cron

```bash
(crontab -l 2>/dev/null; echo "0 * * * * /path/to/focal/sync.sh") | crontab -
```

## File reference

| File | Purpose |
|---|---|
| `setup.sh` | Interactive setup wizard — run once |
| `sync.sh` | Main sync script — run manually or via scheduler |
| `config.example.sh` | Template for `config.sh` |
| `config.sh` | Your personal config — **gitignored, never commit** |
| `status_map.json` | Auto-generated status name mappings — **gitignored** |

## State file

Sync state is stored at `~/.focal/state.json` (configurable in `config.sh`).
It records the last-known status of each tracked issue so Focal can detect what
changed between runs. Delete it to reset the baseline.

## Limitations

- GitHub does not emit webhooks for personal project board changes, so sync is
  poll-based. Frequency is controlled by your scheduler interval.
- Status pushes to origin are best-effort: if an origin project doesn't have a
  matching status option and it can't be auto-fixed, that project is skipped
  with a warning in the log.
- The `gh` token must have `project` scope for both your personal board and any
  origin org projects you want to write to.

## Using with an AI agent (Claude Code, Codex, etc.)

Focal ships with an [AGENTS.md](AGENTS.md) that AI coding agents read
automatically on startup. This means you can set up and manage Focal entirely
through conversation — no need to read documentation manually.

**First-time setup:**
```bash
git clone https://github.com/leninmehedy/focal.git
cd focal
claude        # Claude Code CLI
# or: open the folder in VS Code with the Claude Code extension
```

Once Claude Code is open, just say:
> *"Set up Focal for me"*

Claude will check prerequisites, run the setup wizard, verify the first sync,
and install the scheduler — asking you only for the things it can't infer
(your board URL and which repos to track).

**Ongoing use — things you can ask Claude:**
- *"Add hashgraph/solo-operator to my sync"*
- *"Why is issue #42 still showing as New?"*
- *"Reset and re-sync everything from scratch"*
- *"Show me warnings from the last sync"*
- *"The hourly sync stopped running — what's wrong?"*
