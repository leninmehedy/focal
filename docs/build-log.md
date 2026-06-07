# Focal — Build Log

Running record of what's been shipped, what's in flight, and what's next.
Updated at the end of every session before committing.

---

## ▶ Resume command

Copy-paste this at the start of any new session to get oriented:

```
Read focal/README.md, then focal/CLAUDE.md, then focal/docs/build-log.md — then tell me what to work on next.
```

---

## Status key

| Symbol | Meaning |
|---|---|
| ✅ | Merged to main |
| 🔄 | PR open — pushed, awaiting merge |
| 📋 | Issue open, work not started |

---

## Current state (as of 2026-06-07)

**Last action:** Rebased `feat/134-general-maintenance-epic` on main (resolved conflict in `focal/pm/init_cmd.py` — missing `import re`). Added `docs/build-log.md` and `CLAUDE.md` to the branch.

**Immediate next step:** Push `feat/134-general-maintenance-epic` and force-push PR #136, then wait for merge before starting #135.

---

## In flight

| PR | Issue | Branch | What | State |
|---|---|---|---|---|
| #136 | #134 | `feat/134-general-maintenance-epic` | **E0 General Maintenance epic** — `focal pm init` auto-creates E0; user epics start at E1; AGENTS.md critical warning; CLAUDE.md agent self-write instruction; `docs/build-log.md` + `CLAUDE.md` added | 🔄 Needs push after rebase, then merge |

---

## Up next (after PR #136 merges)

| Issue | Branch (to create) | What |
|---|---|---|
| #135 | `feat/135-pm-triage` | **`focal pm triage owner/repo`** — list open GitHub issues not linked to any epic in local state cache |

### Issue #135 — `focal pm triage` — full implementation notes

Command: `focal pm triage owner/repo`

Flags:
- `--label TEXT` — filter by GitHub label
- `--unassigned` — only show unassigned issues
- `--days N` — only show issues opened in the last N days
- `--json` — output as JSON instead of table

Behaviour:
1. Load `focal-state.json` — collect all issue numbers already tracked (epics + stories).
2. Call `gh issue list --repo owner/repo --state open --json number,title,labels,assignees,createdAt --limit 200`.
3. Subtract tracked issues → untracked remainder.
4. Apply `--label`, `--unassigned`, `--days` filters.
5. Render a rich table: `#` · title · labels · assignee · age.
6. Print hint: `Run focal pm story-create owner/repo --epic E0 --title "..." to track any of these.`

Files to create/edit:
- `focal/pm/triage_cmd.py` — new file (main logic)
- `focal/cli.py` (or `focal/pm/__init__.py`) — wire `triage` subcommand
- `docs/pm-guide.md` — add `focal pm triage` section
- `docs/user-guide.md` — mention triage in "keep cache fresh" section
- `docs/testing-guide.md` — TR1–TR5 test cases
- `AGENTS.md` — add `focal pm triage` to command surface table
- `docs/build-log.md` — move #135 to Shipped after merge

---

## Shipped (merged to main)

| PR | Issue | What |
|---|---|---|
| #132 | #133 | **Fix: templates not included in wheel** — moved `templates/` inside `focal/` package; use `importlib.resources` so `pipx install focal-cli` users get templates without cloning the repo |
| #131 | — | Fix gaps in user-guide, pm-guide, testing-guide |
| #130 | — | Add "Why not just use an AI agent?" section to README |
| #129 | — | README polish pass |
| #128 | — | Move motivation/audience to top of README |
| #127 | — | MCP server — 13 tools exposing all PM and board commands |
| #126 | — | Design doc D003 — Focal MCP server |
| #125 | — | Rewrite why-focal.md |

---

## Permanent rules (enforced by memory)

- **Issue-first** — every task (bug or feature) needs a GitHub issue **before** any code. Unplanned work → E0.
- **Focal commands only** — never use `gh issue create` / `gh issue edit` directly.
- **PR description style** — short benefit-led bullets; technical detail in the review guide body.
- **Focal issue format** — title is plain description only; SP in `| SP | N |` body table; never in title.
- **Link stories to epic on creation** — sub-issues API immediately, not as a follow-up.
- **Check PR state before pushing** — verify PR is not already merged before pushing to its branch.
- **testing-guide.md** — every PR that adds or changes a command must include test cases.
