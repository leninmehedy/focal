# CLAUDE.md — Focal project context

## ▶ Resume command (copy-paste this to start any session)

```
Read CLAUDE.md and run 
  focal cache refresh leninmehedy/focal
  focal pm epics-render
  
then docs/build-log.md, then docs/focal/epics.md.

For every PR listed as 🔄 in "In flight", run:
  gh pr view <N> --json state,title

For any that are MERGED, run the post-merge commands from CLAUDE.md:
  focal pm solo ship <ISSUE> <PR>
  focal pm solo render

Then re-read docs/build-log.md and tell me what to work on next.
```

This repo uses **solo mode** (`"mode": "solo"` in `docs/focal/build-log.json`).
Use `focal pm solo` commands for all task tracking — not `focal pm plan`/`retro`/`status`.

---

## Where we are right now

→ See **[`docs/build-log.md`](docs/build-log.md)** for the full picture:
- What's merged
- What PRs are open and waiting for merge
- What's next
- Implementation notes for the next task

---

## Project management

This project uses [Focal](https://github.com/leninmehedy/focal) for issue tracking
and delivery management.

**Always use `focal` commands to create or update GitHub issues — never use `gh`
directly for issue or project management.**

| Task | Command |
|---|---|
| Create epic | `focal pm epic-create owner/repo --title "..." --sp N` |
| Create story or bug | `focal pm story-create owner/repo --epic EX --title "..."` |
| Unplanned work / bugs | `focal pm story-create owner/repo --epic E0 --title "..."` |
| Check iteration status | `focal pm status owner/repo` |
| Sync board | `focal board sync` |
| Refresh issue cache | `focal cache refresh owner/repo` |

E0 is the General Maintenance epic — always route bugs and unplanned work there.
Every task needs a GitHub issue before work begins.

---

## Critical rules

1. **Issue-first** — create a GitHub issue before writing any code. No exceptions.
2. **Focal commands only** — never call `gh issue create`, `gh issue edit`, or `gh project` directly.
3. **Do not read or run Focal source code** — `AGENTS.md` is the complete reference.
4. **PR description style** — short benefit-led bullets; technical detail in the review guide body.
5. **Focal issue format** — title is plain description only; SP in `| SP | N |` body table.
6. **testing-guide.md** — every PR that adds or changes a command must add test cases.

---

## How to start a new task

1. Check `docs/build-log.md` → "Up next" section.
2. Verify the prerequisite PR is merged: `gh pr view <N> --json state`.
3. Create a new branch: `git checkout -b feat/<issue>-<slug>`.
4. Implement, then run linters: `python3 -m ruff check focal/ && python3 -m ruff format --check focal/`.
5. **Update `docs/build-log.md`** — run `focal cache refresh leninmehedy/focal`, then `focal pm solo start <ISSUE>` (moves Up next → In flight), then `focal pm solo note "<summary>"` to update the Current state line, then `focal pm solo render && focal pm epics-render`.
6. Commit and push, then create PR with `gh pr create`.

> Build-log is updated **before** the PR is created, as part of the same branch/commit. Never make a separate PR just to update it.

---

## After a PR merges / issues are closed

Run all three commands every time a PR lands or issues are bulk-closed:

```bash
focal pm solo ship <ISSUE> <PR>       # move In flight → Shipped
focal pm solo render                  # re-render docs/build-log.md
focal pm epics-render                 # re-render docs/focal/epics.md
```

After the renders complete, update the Current state line:

```bash
focal pm solo note "<what shipped and what is next>"
focal pm solo render
```

If issues were closed directly with `gh issue close`, run the two renders plus a cache refresh first:

```bash
focal cache refresh leninmehedy/focal
focal pm solo render
focal pm epics-render
```

---

## Repo layout (focal-specific)

```
focal/pm/           PM command modules
focal/templates/    Markdown templates bundled inside the package
docs/focal/         Per-project PM docs (created by focal pm init in target repos)
docs/build-log.md   ← Start here for session state
docs/pm-guide.md    Full PM workflow guide
docs/testing-guide.md  Test cases for every command
AGENTS.md           Full command reference for AI agents
```
