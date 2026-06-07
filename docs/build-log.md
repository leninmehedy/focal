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

**Last action:** PR #136 merged. Issues #137 and #138 created from bug reports.
Build-log updated to reflect new state. `docs/update-build-log` branch open for this commit.

**Immediate next step:** Merge this build-log PR, then start on #138 (quick 2 SP fix first, then #137, then #135).

---

## In flight

| PR | Issue | Branch | What | State |
|---|---|---|---|---|
| (this) | — | `docs/update-build-log` | Build-log refresh after PR #136 merge + bug triage | 🔄 |

---

## Up next — priority order

| # | Issue | Branch (to create) | SP | What |
|---|---|---|---|---|
| 1 | #138 | `fix/138-init-missing-board-setup-hint` | 2 | **`focal pm init` next-steps missing `focal board setup`** — when no config exists, prepend step 0 pointing to `focal board setup` |
| 2 | #137 | `feat/137-board-setup-cli-flags` | 5 | **`focal board setup` non-interactive flags** — add `--owner`, `--board-title`, `--create-board`, `--use-board-number`, `--repos`, `--assignee` |
| 3 | #135 | `feat/135-pm-triage` | 3 | **`focal pm triage owner/repo`** — list open GitHub issues not linked to any epic in local state cache |

> **Bug 1 (templates `FileNotFoundError`) = already fixed** by PR #132 (merged 2026-06-07).
> Users on the broken version just need `pipx upgrade focal-cli`.

---

## Implementation notes

### Issue #138 — `focal pm init` next-steps missing `focal board setup` (2 SP)

File: `focal/pm/init_cmd.py` → `run()` function, near the bottom where next-steps are printed.

Change: check `if config is None` (no `~/.focal/config.json`) and prepend step 0:
```python
if config is None:
    console.print(
        "  0. Create your project board first:  "
        "[bold]focal board setup[/bold]"
    )
```
Also consider promoting the "no board config" warning to a more prominent banner at the top of init output.

Docs to update: `docs/testing-guide.md` (add PI-x test case).

---

### Issue #137 — `focal board setup` non-interactive flags (5 SP)

File: `focal/wizard.py` (or wherever `board setup` is wired) — add a non-interactive path when all required flags are provided.

New flags:
- `--owner TEXT` — GitHub username / org
- `--board-title TEXT` — name for the new board (implies `--create-board`)
- `--create-board` / `--use-board-number N` — mutually exclusive
- `--repos TEXT` — comma-separated repos to watch
- `--assignee TEXT` — default assignee

When all required flags are present → skip all prompts, run directly.
When some flags are missing → fall through to interactive mode for missing values only.

Docs to update: `AGENTS.md` command surface table, `docs/user-guide.md` setup section, `docs/testing-guide.md`.

---

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
