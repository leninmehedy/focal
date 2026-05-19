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

**Board sync** — open issues assigned to you flow automatically onto one personal
Kanban board. Status changes you make there push back to every origin project.
Closed or unassigned issues move to Done on their own.

**PM CLI** — epics, stories, iteration planning, retros, and velocity — all in
GitHub issues and markdown, without leaving the terminal.

## Install

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/leninmehedy/focal/main/install.sh)
focal board setup
```

The installer handles Python, pipx, and `focal-cli` in one step.
The wizard creates your GitHub Projects board automatically and asks which repos to watch.

**→ [Full setup and usage guide](docs/user-guide.md)**

## Set up with an AI agent

Open Claude Code (or any agent that can fetch a URL) and paste:

```
Set up Focal from https://raw.githubusercontent.com/leninmehedy/focal/main/AGENTS.md
```

The agent installs Focal, runs the wizard, verifies sync, and sets up the hourly
scheduler — no manual steps required.

Once set up, you can drive everything in plain language:

- *"Add leninmehedy/focal to my sync"*
- *"Plan I1 — 2-week sprint, me and @bob at 8 SP each, starting Monday"*
- *"What's our iteration status?"*
- *"Log the I1 retro — we hit our goal, estimates were a bit off"*

## Docs

| | |
|---|---|
| [User Guide](docs/user-guide.md) | Install, board sync, PM CLI, scheduler, troubleshooting |
| [PM Guide](docs/pm-guide.md) | Full project management workflow — design docs, epics, delivery cycle |
| [Testing Guide](docs/testing-guide.md) | Beta testing — test cases for every command |
| [AGENTS.md](AGENTS.md) | Full command reference for AI agents |
