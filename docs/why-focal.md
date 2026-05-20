# Why Focal?

Open-source maintainers and contributors live in GitHub. Issues are there, PRs are
there, project boards are there. But the moment you try to do real delivery planning —
capacity, iteration scheduling, velocity tracking, impact forecasting — you hit a wall.
GitHub Projects is a Kanban board, not a planning tool. So people reach for Jira,
Linear, or Notion, and suddenly half their project state lives outside GitHub.

That split is where things rot: docs go stale, boards drift, estimates disappear.

**Focal's answer: stay entirely in GitHub, but get the planning layer you've been missing.**

---

## How Focal compares

| Tool | What it gives you | What it costs |
|---|---|---|
| **GitHub Projects alone** | Kanban view | Free — but no capacity planning, velocity, or forecasting |
| **Jira / Linear / Notion** | Full planning suite | Separate system — issues duplicated, context switched, subscription required |
| **ZenHub / Shortcut** | Board overlay on GitHub | Paid seat, another login, another vendor |
| **Spreadsheet planning** | Flexible | Disconnects from actual issue state immediately; manual upkeep |
| **Focal** | Iteration planning, velocity, what-if forecasting | Free, no SaaS, no extra accounts — just `gh` CLI and markdown |

Focal is **zero additional infrastructure**. No database, no hosted service, no
webhook, no API token beyond what `gh` already has. It writes markdown files into
your repo and reads GitHub issues. That's it.

---

## What you actually get

### Iteration planning without leaving the repo

`focal pm plan` generates `docs/focal/iteration-planning.md` directly from your open
issues and SP estimates. The plan is a markdown file — version-controlled,
PR-reviewable, and readable by any contributor without an account or subscription.

### Velocity that tracks itself

`focal pm retro` logs delivered vs carry-over story points per iteration into
`retro-log.md`. After 3–4 iterations you have a real velocity baseline. No
spreadsheet, no manual entry — Focal reads issue close state from GitHub and writes
structured history into the repo.

### What-if forecasting

This is the hardest thing to do in any other free tool. Before committing to a plan:

```bash
# What slips if alice is out next week?
focal pm what-if owner/repo --pto "alice:2026-06-27:2026-07-04"

# What gets pushed if we inject an urgent fix?
focal pm what-if owner/repo --inject "Security patch:8"

# Story 1.3 grew — reforecast the whole plan
focal pm what-if owner/repo --reestimate "1.3:13"
```

Focal shows exactly which stories slip to later iterations — before you touch
anything. Pass `--apply` only when you're happy with the result.

### AI-agent native from day one

Focal ships with [`AGENTS.md`](../AGENTS.md) — a machine-readable command reference
that any capable AI agent (Claude Code, Cursor, Codex) can use to drive the entire
PM workflow without custom prompting:

- Write design docs with structured breakdown hints
- Create epics and stories from those docs in one command
- Run what-if scenarios on request
- Log retros and update velocity

For maintainers who are time-poor, this is the practical payoff: delegate the PM
overhead to an agent that already knows the tool.

### Personal board sync that stays accurate

Multi-repo contributors often maintain a personal GitHub Projects board to see all
their work in one place. Without automation, that board is wrong within a day.
Focal keeps it accurate — open assigned issues flow in automatically, status changes
push back to origin projects, and closed issues move to Done without any manual work.

---

## Who is it for?

The sweet spot is **solo maintainers or small core teams (2–5 people)** running
open-source projects on GitHub who:

- Care about delivery cadence and velocity but don't want to manage a SaaS
- Already use GitHub Issues as their source of truth
- Want planning artifacts (iteration plans, retro logs, design docs) version-controlled
  alongside the code
- Use or want to use AI agents as collaborators

It's not designed for large organisations with dedicated PMs — those teams already have
Jira. It's for the engineer-PM hybrid who wants structure without overhead.

---

## The "just markdown" principle

Every planning artifact Focal produces is a plain markdown file committed to your repo:

| File | What it contains |
|---|---|
| `docs/focal/iteration-planning.md` | Capacity, schedule, story assignments, risks |
| `docs/focal/retro-log.md` | Per-iteration velocity and retrospective history |
| `docs/focal/epics.md` | Epic/story tracker with SP rollups |
| `docs/focal/design/D*.md` | Per-feature design records with breakdown hints |

This is a principled stance against lock-in:

- **Readable by humans** — open the file in GitHub, no login required
- **Readable by AI agents** — context is always available for any tool that can read a file
- **Diffs in PRs** — plan changes are reviewed like code, with full history
- **Survives tool changes** — if Focal disappears tomorrow, your planning history is still in your repo

---

## One-sentence pitch

> *Focal gives GitHub-native open-source projects iteration planning, velocity
> tracking, and what-if forecasting — entirely in markdown and GitHub Issues,
> with no SaaS, no subscription, and full AI-agent support.*
