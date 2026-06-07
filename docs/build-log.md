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

## Current state (as of 2026-06-08)

**Last action:** PR #145 open — CLAUDE.md build-log rule + user-guide full workflow section + issue #146 (`--no-plan` solo mode).

**Immediate next step:** Merge #145, then start #135 — `focal pm triage owner/repo`.

---

## In flight

| PR | Issue | Branch | What | State |
|---|---|---|---|---|
| #145 | — | `docs/claude-md-build-log-rule` | CLAUDE.md build-log rule + user-guide workflow section | 🔄 |

---

## Up next — priority order

| # | Issue | Branch (to create) | SP | What |
|---|---|---|---|---|
| 1 | #135 | `feat/135-pm-triage` | 3 | **`focal pm triage owner/repo`** — list open GitHub issues not linked to any epic in local state cache |
| 2 | #146 | `feat/146-no-plan-mode` | 5 | **`focal pm status --no-plan`** — solo/lightweight mode using build-log.md as tracker |

---

## Implementation notes

### Issue #135 — `focal pm triage owner/repo` (3 SP)

Flags:
- `--label TEXT` — filter by GitHub label
- `--unassigned` — only show unassigned issues
- `--days N` — only show issues opened in the last N days
- `--json` — output as JSON instead of table

Behaviour:
1. Load `focal-state.json` — collect all tracked issue numbers (epics + stories).
2. `gh issue list --repo owner/repo --state open --json number,title,labels,assignees,createdAt --limit 200`
3. Subtract tracked → untracked remainder.
4. Apply filters.
5. Render rich table: `#` · title · labels · assignee · age.
6. Print hint: `Run focal pm story-create owner/repo --epic E0 --title "..." to track any of these.`

Files: `focal/pm/triage_cmd.py` (new), wire subcommand, update `docs/pm-guide.md`, `docs/user-guide.md`, `docs/testing-guide.md` (TR1–TR5), `AGENTS.md`.

---

## Shipped (merged to main)

| PR | Issue | What |
|---|---|---|
| #140 | #137, #138 | **`focal board setup` non-interactive flags + `focal pm init` step-0 board hint** — `--owner`, `--repos`, `--create-board`/`--use-board-number`; step-0 warning when no config |
| #136 | #134 | **E0 General Maintenance epic** — `focal pm init` auto-creates E0; user epics start at E1; AGENTS.md critical warning + CLAUDE.md agent self-write instruction; `docs/build-log.md` + `CLAUDE.md` added |
| #132 | #133 | **Fix: templates not included in wheel** — moved `templates/` inside `focal/` package; `importlib.resources` path resolution |
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
