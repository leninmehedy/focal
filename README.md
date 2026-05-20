# Focal

**For engineers who contribute to many GitHub repos and want structured project
management — without the overhead, without context switching, without leaving
the terminal.**

Focal gives you one personal Kanban board that stays in sync with every project
you contribute to, plus a full PM CLI for running delivery end-to-end: epics,
stories, iteration planning, retros, and velocity — all in GitHub issues and
markdown.

Works entirely from the terminal, no AI required. Add an agent later to
accelerate — not to unlock.

## The problem

If you're an engineer contributing across many repos, planning your day means
opening every project board one by one — context switching before you've written
a single line of code. And when it comes to planning a release, you're either
reaching for a separate PM tool (another context switch) or keeping it in your
head (no record, no accountability).

Most teams also spend energy maintaining the process itself — updating boards,
attending standups for status, fielding "where are we on X?" questions. Focal
makes the process self-maintaining: the board syncs automatically, plans and
retros are committed to the repo, and anyone can see current status without
interrupting the engineer.

**Focal solves this by working inside GitHub — not beside it:**

- **One board, every repo** — open issues assigned to you flow onto a single
  personal Kanban board automatically; status changes push back to every origin
  project
- **GitHub-native, no new tool** — everything Focal creates lives in GitHub
  issues and markdown files; no new login, no new subscription, no data silo
- **PM in the terminal** — epics, stories, iteration planning, retros, velocity
  — all committed alongside your code, readable by anyone with repo access
- **Engineer as their own PM** — planning is a CLI command, not a dashboard to
  maintain; every plan, retro, and design doc lives in git on the same timeline
  as your code
- **What-if before you commit** — model the impact of PTO, scope injection, or
  a re-estimate before touching the plan
- **Opinionated conventions that scale** — every repo initialized with Focal
  works the same way; engineers across many projects never re-learn a planning
  setup
- **Works without an agent** — fully interactive terminal prompts mean no AI
  required; add an agent later to accelerate, not to unlock

**→ [Full breakdown and comparisons](docs/why-focal.md)**

## What it does

**Board sync**

| Without Focal | With Focal |
|---|---|
| Open 5 project boards to see what's assigned to you | One board aggregates everything automatically |
| Update status on your board, then update every origin project board too | Move a card once — status pushes back to every origin project automatically |
| Chase closed issues off your board | Closed or unassigned issues move to Done on their own |

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

> **Built with AI. Best used with AI.**
> Focal ships with [`AGENTS.md`](AGENTS.md) so any capable AI agent can set it
> up, run PM commands, and manage your backlog on your behalf — no manual steps
> required.

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

---

## Docs

| | |
|---|---|
| [Why Focal?](docs/why-focal.md) | The motivation, philosophy, and design principles behind Focal |
| [User Guide](docs/user-guide.md) | Install, board sync, PM CLI, scheduler, troubleshooting |
| [PM Guide](docs/pm-guide.md) | Full project management workflow — design docs, epics, delivery cycle |
| [Testing Guide](docs/testing-guide.md) | Beta testing — test cases for every command |
| [AGENTS.md](AGENTS.md) | Full command reference for AI agents |
