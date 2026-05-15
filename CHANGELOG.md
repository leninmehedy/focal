# [1.1.0](https://github.com/leninmehedy/focal/compare/v1.0.0...v1.1.0) (2026-05-15)


### Features

* rewrite core in Python ([8982ec3](https://github.com/leninmehedy/focal/commit/8982ec351d62d638ae8d86f7e3e73a4bb53cea72))

# 1.0.0 (2026-05-15)

### Features

* bidirectional sync between personal GitHub Projects board and origin repo boards
* pull: open assigned issues added automatically; status inherited from origin
* push: card moves on personal board propagate to all origin projects
* stale detection: closed or unassigned issues moved to Done automatically
* conflict resolution: personal board wins when both sides change
* emoji-normalized status matching (`🏗 In progress` = `In progress`)
* status_map.json fallback for origin projects with incompatible status names
* interactive setup wizard with three repo selection modes
* structured daily-rotating logging to `~/.focal/logs/`
* macOS launchd agent template for hourly sync
* rewritten core in Python (typer CLI, rich terminal output)
* AGENTS.md for AI agent onboarding (Claude Code, Codex, etc.)

### Bug Fixes

* fixed silent exit under launchd when stdout is not a terminal
* fixed status inheritance running before new items were written to state
* fixed action parsing breaking on status names containing spaces
* fixed stale detection using hardcoded `Done` instead of configured `DONE_STATUS`
