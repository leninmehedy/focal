# Why Focal?

Most open-source projects don't have a dedicated PM. They have engineers who also
have to plan, estimate, track velocity, and make delivery decisions — often on top
of their day jobs. The tooling built for that work was designed for full-time PMs
in funded teams with dedicated process budgets. It doesn't fit how engineers think
or work, so most open-source projects either skip planning entirely or do it badly
in a spreadsheet.

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

## 4. GitHub-native — no new tool to learn or maintain

Most PM tools sit *beside* GitHub. You close a PR, then open a separate tool to
move the ticket. You finish a sprint, then export a report somewhere else. You
onboard a new contributor, then give them a login to yet another system. Every
hand-off is a context switch, and every context switch is a place where discipline
erodes.

Focal works *inside* GitHub. Everything it creates — issues, markdown files,
project board items — is standard GitHub. No new login. No subscription. No
data in a SaaS database that only some people can access.

This means:

- **Any engineer with repo access can read the full project state** — iteration
  plan, retro history, design docs — without installing Focal or touching a
  separate tool
- **The delivery record survives tool changes** — if Focal disappears tomorrow,
  everything it created is still in your repo, in plain text, forever
- **Focal aligns with GitHub best practices** rather than replacing them — issue
  templates, labels, sub-issues, and Projects v2 are used as designed, just
  wired together consistently

There's also a subtler benefit: **the process becomes self-maintaining**. Most
teams spend real time on process overhead — updating boards after standups,
fielding "where are we on X?" questions, chasing engineers for status. Focal
eliminates that ceremony. The board syncs automatically. Plans and retros are
committed to the repo. Anyone who wants current status reads the repo; nobody
has to interrupt the engineer to ask.

---

## 5. Opinionated conventions that scale across projects

Focal is opinionated by design. Every repo that runs `focal pm init` gets the same
structure: the same file layout, the same issue templates, the same iteration
planning format, the same retro log schema.

For an engineer contributing to five different open-source projects, this means
**every project works the same way**. There's no re-learning a new planning
convention, no deciphering a custom spreadsheet, no figuring out which template
or tool this team chose. The mental model transfers immediately.

This is the alternative to two failure modes that plague open-source projects today:

- **Chaos** — every project invents its own planning setup (or skips it entirely),
  making cross-project contribution expensive and context-switching constant
- **Over-engineering** — a well-meaning contributor introduces a heavyweight PM
  process that the rest of the team can't maintain

Focal's conventions are lightweight enough to adopt in minutes (`focal pm init`),
structured enough to produce real planning artifacts, and consistent enough that
familiarity with one project immediately transfers to the next.

The opinions aren't arbitrary either — they reflect real delivery best practices:
design docs before backlog creation, SP estimation at the story level, iteration
goals tied to retros, slip reasons tracked per story. Engineers who follow the
workflow naturally build good delivery habits without needing a PM to enforce them.

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

## 6. Works without an agent — better with one

Focal does not require an AI agent. Every command runs interactively in the
terminal, prompting for inputs when flags aren't supplied:

```
$ focal pm epic-create automa-saga/automa
  Title: Add distributed tracing
  Description: Instrument all service boundaries with OpenTelemetry.
  Estimate (SP): 13
  ✔ Created issue #47
  ✔ Added to project board
  ✔ docs/focal/epics.md updated (E4)
```

No agent, no config, no API key beyond what `gh` already has. An engineer on a
fresh machine with only `gh` and Focal installed can run the full delivery
workflow — plan an iteration, log a retro, run a what-if — entirely from the
terminal, entirely without AI.

The agent support is an accelerator, not a requirement. The same workflow exists
on a spectrum:

| Mode | How it works | What the engineer does |
|---|---|---|
| **Terminal only** | Interactive prompts for every input | Types answers, reviews output |
| **Terminal + agent** | Agent supplies non-interactive flags | Reviews and approves |
| **Fully delegated** | Agent reads design docs, creates backlog, runs what-if, logs retros | Merges PRs |

All three modes produce identical artifacts and the same git history. The agent
removes keystrokes — it doesn't change what gets created or how it's stored.

This matters for adoption: an engineer can start using Focal today, on any machine,
without setting up an AI environment. If they later add an agent, the workflow
accelerates without any migration or reconfiguration. And on machines where an
agent isn't available — a remote server, a pairing session, a locked-down
corporate laptop — Focal still works exactly as designed.

---

## Who it's for

Focal is built for **engineers running their own open-source projects** — solo
maintainers or small core teams (2–5 people) who:

- Want structured delivery without the overhead of a PM role or a PM tool
- Use GitHub Issues as their source of truth and want to keep it that way
- Want their planning history version-controlled alongside their code
- Work with or want to use AI agents as collaborators

It is not built for large organisations with dedicated PMs and established tooling
— those teams already have what they need. Focal is for the engineer who has
always wanted to run their projects well but found existing tools too heavy, too
expensive, or too far from where the actual work happens.

---

## The one-sentence version

> *Focal lets engineers run their own projects at a professional level — planning,
> velocity, and forecasting — entirely inside GitHub and git, with no new tool to
> learn, no process ceremony to maintain, and full AI-agent support.*
