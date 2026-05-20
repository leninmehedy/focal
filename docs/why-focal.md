# Why Focal?

Most open-source projects don't have a dedicated PM. They have engineers who also
have to plan, estimate, track velocity, and make delivery decisions — often on top
of their day jobs. The tooling built for that work (Jira, Linear, Notion) was
designed for full-time PMs in funded teams. It doesn't fit how engineers think or
work, so most open-source projects either skip planning entirely or do it badly in
a spreadsheet.

Focal is built on a different premise: **every engineer can run their own projects
at a professional level, without needing a dedicated PM — if the tooling gets out
of their way.**

---

## 1. Engineer as their own PM

Focal is a CLI tool. Planning is a command you run, not a dashboard you maintain.

```bash
focal pm plan automa-saga/automa --weeks 2 --start 2026-06-02 --team "me:8"
focal pm retro automa-saga/automa --iteration I1 --goal-met
focal pm what-if automa-saga/automa --pto "me:2026-06-27:2026-07-04"
```

There are no ticket views to configure, no board columns to drag, no reporting
dashboards to set up. The output is a markdown file in your repo. The workflow is
the same whether you're a team of one or five.

For engineers who live in the terminal, this means **planning never requires leaving
the console**. No browser tab, no login, no context switch. You can plan an
iteration, run a what-if scenario, and log a retro in the same session where you
just pushed code.

This matters because the barrier to structured delivery isn't willingness — most
engineers care about shipping well. The barrier is that PM tools impose a PM's
mental model on people who think in code, commits, and terminals. Focal meets
engineers where they are.

---

## 2. Git is the system of record

Every planning artifact Focal produces is a plain markdown file committed to your
repo, on the same timeline as your code:

| File | What it captures |
|---|---|
| `docs/focal/design/D*.md` | Problem framing, design decisions, breakdown hints |
| `docs/focal/epics.md` | Epic/story tracker with SP rollups |
| `docs/focal/iteration-planning.md` | Capacity, schedule, story assignments |
| `docs/focal/retro-log.md` | Velocity, slip reasons, retrospective history |

This is not just convenience — it's a fundamentally different model from every
other planning tool.

**The delivery trail lives with the code.** A new contributor can `git log` and
understand not just what changed, but why it was planned that way — which stories
were carried over and why, what the velocity looked like, what tradeoffs were made
during planning. That context is usually locked inside a PM tool that only some
people have access to, or lost entirely.

**AI agents can read it natively.** No integrations, no API keys, no special
tooling. An agent that can read a file can read your entire project history —
design rationale, iteration plans, retro notes — and contribute meaningfully. This
is what "AI-native" actually means in practice: context that lives in files, not in
a SaaS database.

**It survives tool changes.** If Focal disappears tomorrow, your planning history
is still in your repo, readable by anyone, forever. No export required.

---

## 3. What-if before you commit

Most planning tools tell you what happened. Focal helps you decide what to do
*before it happens*.

Before finalising a plan, you can model the consequences of real-world disruptions:

```bash
# Alice is out for a week — what slips?
focal pm what-if automa-saga/automa --pto "alice:2026-06-27:2026-07-04"

# A security issue just landed — what gets pushed if we absorb it?
focal pm what-if automa-saga/automa --inject "CVE patch:8"

# Story 2.3 is bigger than we thought — reforecast
focal pm what-if automa-saga/automa --reestimate "2.3:13"
```

Focal shows exactly which stories slip to later iterations — before you touch
anything. The plan doesn't change until you pass `--apply`.

This kind of active decision support used to require a PM who knew the tool well
enough to run scenarios manually. Now any engineer can run it in seconds, as often
as needed, with the actual plan data — not a copy of it in a spreadsheet.

---

## Who it's for

Focal is built for **engineers running their own open-source projects** — solo
maintainers or small core teams (2–5 people) who:

- Want structured delivery without the overhead of a PM role or a PM tool
- Use GitHub Issues as their source of truth and want to keep it that way
- Want their planning history version-controlled alongside their code
- Work with or want to use AI agents as collaborators

It is not built for large organisations with dedicated PMs. Those teams have Jira,
and they should keep using it. Focal is for the engineer who has always wanted to
run their projects well but found existing tools too heavy, too expensive, or too
far from where the actual work happens.

---

## The one-sentence version

> *Focal lets engineers run their own projects at a professional level — planning,
> velocity, and forecasting — entirely inside GitHub and git, with no SaaS, no PM
> role required, and full AI-agent support.*
