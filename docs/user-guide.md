# Focal User Guide

This guide walks you through everything Focal can do, from first install to
running delivery end-to-end. Read it top to bottom the first time, then use
it as a reference.

---

## How Focal works — the mental model

Focal is two independent tools that share a config:

```
┌─────────────────────────────────────────────────────────┐
│  Board sync                                             │
│  Watches repos you choose → pulls assigned issues onto  │
│  your personal GitHub Projects board automatically.     │
│  No setup needed inside those repos.                    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  PM CLI                                                 │
│  Full project management inside a specific repo —       │
│  epics, stories, iteration planning, retros, velocity.  │
│  Requires focal pm init in that repo first.             │
└─────────────────────────────────────────────────────────┘
```

You can use board sync without ever touching the PM CLI, and vice versa.

---

## Part 1 — Board sync

### What you need first

1. **`gh` CLI** installed and authenticated:
   ```bash
   brew install gh          # macOS
   gh auth login            # follow the prompts
   gh auth refresh -s project   # add project scope if missing
   ```

2. **A personal GitHub Projects v2 board** at
   `https://github.com/users/YOUR_USERNAME/projects`:
   - Click **New project → Board** layout
   - Add a **Status** single-select field with these recommended options:
     ```
     🆕 New  ·  📋 Backlog  ·  🔖 Ready  ·  🏗 In progress  ·  ✋ Blocked  ·  👀 In review  ·  ✅ Done
     ```
   - Note the project number from the URL (e.g. `projects/3`)

3. **Focal installed:**
   ```bash
   pipx install focal-cli
   ```
   If you don't have pipx: `pip3 install pipx && pipx ensurepath`, then restart your terminal.

### First-time setup

```bash
focal board setup
```

The wizard asks for:
- Your personal board URL (e.g. `https://github.com/users/you/projects/3`)
- Your GitHub username
- Which column is your Done column
- Which repos to watch

You can add as many repos as you like. Focal will watch all of them and pull
issues assigned to you onto your personal board.

Config is saved to `~/.focal/config.json`. It never touches any of your repos.

### Run your first sync

```bash
focal board sync
```

Open your board — all open issues assigned to you across the repos you listed
should now be there. Each new issue inherits its status from the origin project.

Last line of output will be:
```
Sync complete — added: 5  inherited: 5  pushed: 0  stale: 0  (full)
```

Subsequent syncs are incremental — only issues updated since the last run are
re-fetched, so they're much faster.

### Check your board at a glance

```bash
focal board status
```

Shows a count of issues per Status column, any blocked items, and issues added
in the last 7 days — without running a sync.

### How bidirectional sync works

| What you do | What Focal does on next sync |
|---|---|
| Move a card on your personal board | Pushes the new status to all origin projects that issue belongs to |
| Issue is closed on GitHub | Moves card to your Done column |
| Issue is unassigned from you | Moves card to your Done column |
| New issue assigned to you | Adds it to your board, inheriting origin status |

Your personal board always wins on conflict — if both sides changed between
syncs, your board's status is pushed to origin.

### Adding or removing repos

Re-run the wizard:
```bash
focal board setup
```
Choose **Add repos** to append more, **Edit repo list** to change the full list,
or **Full reconfigure** to start over. Alternatively edit `~/.focal/config.json`
directly — the `repos` array.

### Automating sync (run every hour)

**macOS:**
```bash
cp /path/to/focal/launchd/com.your-username.focal.plist \
   ~/Library/LaunchAgents/com.YOUR_USERNAME.focal.plist
# Edit the plist: replace YOUR_USERNAME and /path/to/focal
launchctl load ~/Library/LaunchAgents/com.YOUR_USERNAME.focal.plist
```

**Linux:**
```bash
(crontab -l 2>/dev/null; echo "0 * * * * focal board sync >> ~/.focal/logs/sync.log 2>&1") | crontab -
```

### Logs

Every sync writes to `~/.focal/logs/YYYY-MM-DD.log`:
```bash
tail -f ~/.focal/logs/$(date '+%Y-%m-%d').log   # follow live
grep WARN ~/.focal/logs/*.log                    # see warnings
```

---

## Part 2 — PM CLI

The PM CLI manages your entire delivery lifecycle inside a specific repo. You
can use it on any repo you own or contribute to — it creates GitHub issues,
links sub-issues, writes markdown planning docs, and keeps everything in sync.

**Important:** Board sync and PM CLI are separate. A repo doesn't need
`focal pm init` for issues to appear on your personal board — board sync just
needs the repo in your `repos` list. `focal pm init` is only needed when you
want Focal to manage delivery inside that repo.

### Bootstrap a repo

```bash
cd ~/code/myorg/my-project
focal pm init myorg/my-project
```

This creates:
```
.github/ISSUE_TEMPLATE/epic.md
.github/ISSUE_TEMPLATE/story.md
docs/focal/epics.md
docs/focal/iteration-planning.md
docs/focal/retro-log.md
docs/focal/design/
```

It also creates `epic` and `story` labels on GitHub, and registers the repo in
`~/.focal/config.json` so cache refresh includes it automatically.

Safe to re-run — existing files are never overwritten.

### Build your backlog

**Create an epic** (a large body of work, typically 10–30 SP):
```bash
focal pm epic-create myorg/my-project --title "User authentication" --sp 21
# → creates GitHub issue #42 with label `epic`, ID E1
```

**Create stories** (individual tasks under an epic, typically 3–8 SP):
```bash
focal pm story-create myorg/my-project --epic E1 --title "GitHub OAuth flow" --sp 5
focal pm story-create myorg/my-project --epic E1 --title "Session management" --sp 3
# → creates issues #43, #44 linked as sub-issues of #42, IDs 1.1 and 1.2
```

Run interactively (no flags) to be prompted for each field.

### Plan an iteration

```bash
focal pm plan myorg/my-project \
  --weeks 2 \
  --start 2026-06-02 \
  --team "alice:8,bob:6"
```

Generates `docs/focal/iteration-planning.md` with:
- Iteration schedule (I1, I2, … across the planning horizon)
- Capacity per person with PTO reduction
- Stories greedily assigned to fill each iteration
- Risk register for stories with missing estimates

Optional flags:
- `--pto "alice:2026-06-09:2026-06-13"` — reduce capacity for leave (repeatable)
- `--goals "I1:Ship auth,I2:Close E2"` — set a goal per iteration

### Check iteration progress

```bash
focal pm status myorg/my-project
```

Shows a live terminal dashboard: progress bar, SP delivered vs planned, list of
stories with assignee and project status. Add `--refresh` to pull latest GitHub
state first.

### Log a retro

At the end of each iteration:
```bash
focal pm retro myorg/my-project \
  --iteration I1 \
  --goal-met \
  --went-well "Good collaboration" \
  --to-improve "Estimation accuracy" \
  --action "alice:Re-estimate carry-overs:2026-06-10"
```

Appends a structured block to `docs/focal/retro-log.md` with delivered vs
carry-over stories, velocity metrics, and retrospective notes.

### View historical velocity

```bash
focal pm velocity myorg/my-project
```

Reads `docs/focal/retro-log.md` and shows a table of planned vs delivered SP,
carry-over, and efficiency per iteration — no GitHub API calls needed.

### Keep the cache fresh

Focal maintains a local cache of issue states so `plan`, `status`, and `retro`
work fast without hitting GitHub on every run. The cache can drift when issues
are updated directly on GitHub.

```bash
focal cache refresh myorg/my-project    # refresh one repo
focal cache refresh-all                 # refresh all registered repos
focal cache status                      # check how stale each repo's cache is
```

Schedule twice-daily refresh on macOS:
```bash
cp /path/to/focal/launchd/com.your-username.focal-cache.plist \
   ~/Library/LaunchAgents/com.YOUR_USERNAME.focal-cache.plist
# Edit: replace YOUR_USERNAME and /path/to/focal
launchctl load ~/Library/LaunchAgents/com.YOUR_USERNAME.focal-cache.plist
```

### Stop tracking a repo

```bash
focal pm remove-repo myorg/my-project
```

Removes the repo from `pm_repos` in `~/.focal/config.json` so it's no longer
included in `refresh-all`. Does not delete any local files.

---

## Part 3 — AI-native workflow

Focal is designed to be driven by an AI agent. Every command has full
non-interactive flags so an agent can run it without answering prompts.

With Claude Code (or any agent that reads `AGENTS.md`):

```
"Set up Focal for me"
"Add myorg/my-project to my sync"
"Read our design doc and create the epics and stories"
"Plan I1 — 2-week sprint, me and @bob at 8 SP each, starting Monday"
"What's our iteration status?"
"Log the I1 retro — we hit our goal, no blockers, estimates were a bit off"
```

The agent reads `AGENTS.md` automatically, so it already knows every command,
flag, and workflow before you ask.

---

## Part 4 — Day-to-day reference

### Common commands

```bash
# Check what's on your board right now
focal board status

# Sync your board (manually)
focal board sync

# Check iteration progress
focal pm status myorg/my-project

# Refresh cache before checking status
focal pm status myorg/my-project --refresh

# See velocity history
focal pm velocity myorg/my-project

# Check cache health across all repos
focal cache status
```

### Config location

Everything lives in `~/.focal/`:
```
~/.focal/config.json      # your board, repos, and PM settings
~/.focal/state.json       # board sync state (delete to reset)
~/.focal/status_map.json  # status name translations
~/.focal/logs/            # daily sync logs
```

### Start over

```bash
focal reset
```

Removes all config, state, logs, and scheduler plists. Run `focal board setup`
afterwards to reconfigure from scratch.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `gh: command not found` | Install gh CLI: `brew install gh` |
| `focal: command not found` | Run `pipx ensurepath` then restart terminal |
| `Focal is not configured` | Run `focal board setup` first |
| `project scope missing` | Run `gh auth refresh -s project` |
| Issues not appearing after sync | Check `~/.focal/logs/` for warnings |
| Cache feels stale | Run `focal cache refresh myorg/my-project` |
| Want a clean slate | Run `focal reset` then `focal board setup` |
