# Changelog

All notable changes to Focal are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Focal uses [Semantic Versioning](https://semver.org/).

---

## [1.0.0] — 2026-05-15

First public release.

### The problem it solves

Contributors involved in many GitHub repositories each have their own project
board. Keeping track of what is assigned, what is in progress, and what to
prioritize means jumping between boards constantly. Focal creates a single
personal Kanban board that stays bidirectionally in sync with every origin
project board — so you plan and prioritize in one place, and status changes
flow back to your teammates automatically.

### Features

- **Pull** — Open issues assigned to you are automatically added to your
  personal board. New items inherit their status from the origin project.
- **Push** — Moving a card on your personal board pushes the status change
  to all origin projects the issue belongs to.
- **Stale detection** — Issues that are closed or unassigned are automatically
  moved to Done on your personal board.
- **Conflict resolution** — Your personal board wins. If both sides change
  between syncs, your board's status is pushed to origin.
- **Emoji-normalized status matching** — `🏗 In progress` and `In progress`
  are treated as the same status, so cosmetic differences between boards don't
  break the sync.
- **Status map fallback** — For origin projects with incompatible status names
  (e.g. `Todo` vs `🆕 New`), a `status_map.json` is generated at setup time
  to translate names at sync time.
- **Interactive setup wizard** (`setup.sh`) — checks prerequisites, prompts
  for board URL and repos, inspects and aligns Status columns across all origin
  projects, and generates `config.sh`.
- **Three repo selection modes** — manual list, interactive browser, or full
  scan of all accessible repos.
- **Structured daily logging** — one log file per day at `~/.focal/logs/`,
  with `[INFO ]` / `[WARN ]` / `[ERROR]` levels and a summary line every run.
- **macOS launchd scheduling** — ships with a ready-to-use plist for hourly
  sync that survives sleep/wake cycles and starts on login.
- **Linux / cron support** — one-liner cron setup as an alternative.
- **AI agent ready** — ships with `AGENTS.md` so Claude Code, Codex, and
  other coding agents can set up and manage Focal through conversation.
- **No extra dependencies** — only requires `gh` CLI (authenticated) and
  Python 3 standard library.

### Bug fixes included in v1.0.0

- Fixed silent exit under launchd when stdout is not a terminal (`set -e`
  treated the false return of `[[ -t 1 ]]` as fatal).
- Fixed status inheritance for new board items — items were being written to
  state before origin status could be fetched.
- Fixed action parsing breaking on status names containing spaces (e.g.
  `🏗 In progress`) by switching the action queue to NDJSON format.
- Fixed stale detection incorrectly using `Done` instead of the configured
  `DONE_STATUS` value.
