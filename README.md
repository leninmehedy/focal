# sync-gh-board

Bidirectional sync between your personal GitHub Projects Kanban board and
origin repo project boards across any number of repositories.

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
git clone https://github.com/leninmehedy/sync-gh-board.git
cd sync-gh-board
chmod +x setup.sh sync.sh
./setup.sh
```

`setup.sh` will guide you through everything interactively and generate `config.sh`.

Then run a sync manually:

```bash
./sync.sh
```

## Selecting repos

During `setup.sh` you can choose one of three modes:

| Mode | Description |
|---|---|
| **Manual list** | Type repos one by one (`owner/repo`) |
| **Interactive select** | Browse and pick from your accessible repos |
| **Full scan** | Scans ALL repos you have access to (slow — may take minutes) |

You can edit the `REPOS` array in `config.sh` at any time to add or remove repos.

## Status column alignment

`setup.sh` inspects the Status columns of every origin project and compares them
to your personal board. It will:

1. **Report** any mismatches (missing options, different names)
2. **Offer to fix** them by adding missing options to origin projects
3. **Generate `status_map.json`** as a fallback for projects it cannot fix
   (e.g. projects you don't own) — this maps origin status names to your
   personal board names at sync time

Recommended personal board Status columns (consistent with the emoji set used
by Solo Weaver / Solo Operator style projects):

```
🆕 New  ·  📋 Backlog  ·  🔖 Ready  ·  🏗 In progress  ·  ✋ Blocked  ·  👀 In review  ·  ✅ Done
```

Status matching is emoji-normalized — `🏗 In progress` and `In progress` are
treated as the same status, so minor cosmetic differences don't break the sync.

## Logging

Logs are written to `~/.sync-gh-board/logs/YYYY-MM-DD.log` (one file per
day, naturally self-rotating). Override the directory via `LOG_DIR` in
`config.sh`. When running interactively, logs are also printed to stdout.

**Format:**
```
[2026-05-15 17:09:10] [INFO ] Board: #3 (PVT_kwHOAAxhrc4BXwuQ)
[2026-05-15 17:09:14] [INFO ] Adding: https://github.com/hashgraph/solo-operator/issues/1005
[2026-05-15 17:09:47] [WARN ] 'In Progress' not found in "some-org's project" — skipping
[2026-05-15 17:31:22] [INFO ] Sync complete — added: 3  inherited: 3  pushed: 1  stale: 0  log: /...
```

**Severity levels:** `[INFO ]`, `[WARN ]`, `[ERROR]`

**Summary line** — every run ends with a count of: issues added, statuses
inherited from origin, statuses pushed to origin, and stale items moved to Done.

View today's log:
```bash
tail -f ~/.sync-gh-board/logs/$(date '+%Y-%m-%d').log
```

Grep for warnings:
```bash
grep '\[WARN\]' ~/.sync-gh-board/logs/*.log
```

## Recurring sync

Add a cron job to sync every hour (no log redirect needed — sync.sh handles it):

```bash
(crontab -l 2>/dev/null; echo "0 * * * * /path/to/sync-gh-board/sync.sh") | crontab -
```

## File reference

| File | Purpose |
|---|---|
| `setup.sh` | Interactive setup wizard — run once |
| `sync.sh` | Main sync script — run manually or via cron |
| `config.example.sh` | Template for `config.sh` |
| `config.sh` | Your personal config — **gitignored, never commit** |
| `status_map.json` | Auto-generated status name mappings — **gitignored** |

## State file

Sync state is stored at `~/.sync-gh-board/state.json` (configurable
in `config.sh`). It records the last-known status of each tracked issue so the
sync can detect what changed between runs. Delete it to reset the baseline.

## Limitations

- GitHub does not emit webhooks for personal project board changes, so sync is
  poll-based. Frequency is controlled by your cron interval.
- Status pushes to origin are best-effort: if an origin project doesn't have a
  matching status option and it can't be auto-fixed, that project is skipped
  with a warning in the log.
- The `gh` token must have `project` scope for both your personal board and any
  origin org projects you want to write to.

## Using with Claude Code

See [CLAUDE.md](CLAUDE.md) for instructions on using Claude Code to manage and
extend this tool.
