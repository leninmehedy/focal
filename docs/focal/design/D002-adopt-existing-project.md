---
id: D002
title: Adopt an existing project into Focal PM management
author: @leninmehedy
status: Draft
created: 2026-05-19
updated: 2026-05-19
relates-to: D001
---

# D002 — Adopt an existing project into Focal PM management

## Abstract

`focal pm adopt` scans an existing GitHub repo for issues that represent
epics and stories — regardless of how they are currently labelled or
structured — maps them into Focal's internal state, and bootstraps the
local PM cache so that `focal pm status`, `plan`, `retro`, and `what-if`
can take over management immediately. An optional `--normalise` flag
re-labels and re-formats issues to match Focal conventions.

## Problem

Focal's value proposition is a **single, standardised view** across every
project an engineer contributes to. That only works if every project speaks
the same format: `epic`/`story` labels, SP in a body table, sub-issue links
for hierarchy. In practice, projects accumulate years of organic issue
structure before Focal arrives:

- Different label conventions per repo: `feature`, `task`, `enhancement`,
  `bug`, or no labels at all
- SP estimates scattered across titles (`[13]`), prose sentences
  (`Estimated: 5 SP.`), project custom fields, or missing entirely
- Parent/child relationships implied by title prefixes (`[Epic] …`),
  body prose, or completely absent — no machine-readable link
- The local `focal-state.json` cache doesn't exist, so `focal pm status`
  immediately errors: *"No iterations in local state"*

This inconsistency is exactly the problem Focal exists to solve — but
without an adoption path, teams working on existing repos are locked out.
`focal pm init` only works on a clean repo; it cannot bootstrap from
existing state.

The result: teams that want to migrate to Focal have to manually relabel
every issue, re-enter SP estimates, and reconstruct the hierarchy from
scratch — a multi-hour task that usually doesn't happen.

A concrete example: `leninmehedy/focal` itself has epics (#69, #82) and
stories but is not managed by Focal because the state cache has never been
bootstrapped for this repo.

## Focal issue format standard

Before adoption can normalise issues, there must be a clear target format.
Focal's canonical format for GitHub issues:

| Field | Epic | Story |
|-------|------|-------|
| Label | `epic` | `story` |
| Title | Plain description — no SP, no prefix | Plain description — no SP, no prefix |
| Body | Summary + stories checklist | `Part of #<epic_number>`<br>`\| SP \| N \|`<br>`\|---\|---\|` |
| Sub-issues | Stories linked via sub-issues API | — |

SP **never** belongs in the title. It lives in the body table so it can be
updated without polluting git history via title changes.

## Goals

- ✅ Scan a repo's GitHub issues and identify epics and stories using
  configurable label mapping (e.g. `feature` → epic, `task` → story)
- ✅ Extract SP estimates from multiple sources: title pattern `[N]` or
  `(N SP)`, body table row `| SP | N |`, GitHub Projects custom field
- ✅ Detect parent/child relationships from GitHub sub-issues API, or
  infer from body mentions (`Part of #N`) and title prefixes
- ✅ Bootstrap `focal-state.json` from discovered issues so all PM
  commands work immediately after adopt
- ✅ Produce a clear adoption report: what was found, what was mapped,
  what couldn't be resolved (missing SP, orphaned stories)
- ✅ Dry-run by default — no GitHub writes, no file writes
- ✅ `--normalise` flag: re-label issues to `epic`/`story`, move SP from
  title to body table, add missing SP, create sub-issue links — all
  opt-in and reversible
- ✅ Safe to re-run: adopting a repo that's already partially managed
  merges discovered state with existing cache rather than overwriting

## Non-goals

- ❌ Automatic SP estimation for issues with no estimate — surfaces as
  a warning; human must fill in or use `--default-sp N` as a fallback
- ❌ Retroactive iteration assignment — adopt only builds the backlog;
  run `focal pm plan` afterwards to assign stories to iterations
- ❌ Migrating from Jira/Linear/Asana — only GitHub Issues as source
- ❌ Bulk closing or archiving of issues not matching any pattern

## User stories

- As an **engineer**, I want to run `focal pm adopt leninmehedy/focal`
  and have Focal scan the existing epics and stories, so that I can
  immediately run `focal pm status` without any manual relabelling.

- As a **tech lead** migrating a team repo to Focal, I want to run
  `focal pm adopt myorg/my-project --epic-label feature --story-label task`
  to map our existing labels, so I don't have to rename 80 issues by hand.

- As an **engineer**, I want `focal pm adopt --normalise` to re-label
  issues and add missing SP estimates to issue bodies, so the repo
  fully conforms to Focal conventions after migration.

- As an **engineer**, I want to run adopt on a repo that's already
  partially managed by Focal and have it merge rather than overwrite,
  so I don't lose state already captured by `focal pm epic-create`.

## Design

### Overview

```
focal pm adopt leninmehedy/focal \
  --epic-label epic \          # default; accepts comma-separated list
  --story-label story \        # default
  --sp-field "Story Points" \  # GitHub Projects field name for SP
  --normalise                  # opt-in: re-label + link sub-issues
```

### Discovery pipeline

```
GitHub Issues (all open + recently closed)
        │
        ▼
  ┌─────────────┐
  │   Filter    │  label ∈ epic_labels → candidate epics
  │             │  label ∈ story_labels → candidate stories
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  SP extract │  1. GitHub Projects field (most authoritative)
  │             │  2. Title pattern: [13] or (13 SP) or #13SP
  │             │  3. Body table: | SP | 13 | or | Story Points | 13 |
  │             │  4. Default (--default-sp) or None (warning)
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  Hierarchy  │  1. GitHub sub-issues API (authoritative)
  │  inference  │  2. Body mention: "Part of #N" / "Parent: #N"
  │             │  3. Title prefix: "[Epic N]" or "E1:"
  │             │  4. Orphaned (no parent found → top-level story, warn)
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  Assign IDs │  E1, E2, … for epics (sorted by issue number)
  │             │  1.1, 1.2, … for stories under each epic
  └──────┬──────┘
         │
         ▼
  Adoption report (terminal) + bootstrap focal-state.json (if --apply)
```

### Components

| Component | Role |
|---|---|
| `focal/pm/adopt_cmd.py` | Main command — orchestrates discovery, extraction, hierarchy, report |
| `focal/pm/sp_extractor.py` | SP extraction from multiple sources |
| `focal/pm/hierarchy_resolver.py` | Parent/child relationship detection |
| `focal/gh.py` | Extended: `issues_by_label()`, `issue_sub_issues()`, `project_field_value()` |
| `focal/_cli.py` | New `focal pm adopt` command registration |

### Data / schema

No new on-disk format. Adoption populates the same `focal-state.json`
structure that `epic-create` and `story-create` write:

```json
{
  "epics": [
    {
      "id": "E1",
      "issue_number": 69,
      "title": "What-if impact assessment",
      "sp": 34,
      "url": "https://github.com/leninmehedy/focal/issues/69",
      "stories": ["1.1", "1.2", "1.3"]
    }
  ],
  "stories": [
    {
      "id": "1.1",
      "epic_id": "E1",
      "issue_number": 70,
      "title": "Extract shared plan helpers",
      "sp": 3,
      "status": "open",
      "assignee": "leninmehedy",
      "url": "https://github.com/leninmehedy/focal/issues/70"
    }
  ],
  "iterations": [],
  "last_synced": "2026-05-19T10:00:00+00:00"
}
```

`iterations` is left empty — run `focal pm plan` after adopt to schedule.

### Adoption report (terminal output)

```
  ◎  Focal — adopt leninmehedy/focal

Scanning issues...
  Found 12 issues with label 'epic' or 'story'

Epics discovered (2)
  E1  #69  What-if impact assessment         34 SP   9 stories
  E2  #8   PyPI distribution                  — SP ⚠ missing estimate

Stories discovered (10)
  1.1  #70  Extract shared plan helpers        3 SP  ✔ linked to E1
  1.2  #71  Implement iteration_parser.py      5 SP  ✔ linked to E1
  ...
  2.1  #?   (orphaned story — no parent found) 5 SP  ⚠ no epic

Warnings (2)
  ⚠  #8 — no SP estimate found (use --default-sp or add to issue body)
  ⚠  #?? — story has no parent epic (will be added as orphan)

Summary
  2 epics  ·  10 stories  ·  0 iterations (run focal pm plan next)
  Dry run — no files written. Pass --apply to bootstrap state cache.
```

### Normalise mode (`--normalise`)

When `--normalise` is passed alongside `--apply`:

1. Re-label any issues using non-standard labels to `epic` or `story`
2. Add SP to issue body as a table row if not already present
3. Create GitHub sub-issue links for stories whose parent was inferred
   (not already linked via the sub-issues API)

Each action is logged and reversible (labels can be removed, sub-issue
links can be deleted via the API).

### Key decisions

| Decision | Rationale |
|----------|-----------|
| Dry-run by default | Adoption touches existing issues; accidental mutation would be hard to undo |
| SP extraction priority order | Project field is most explicit; title pattern is common convention; body table is Focal's own format — authoritative sources first |
| Orphaned stories become top-level in state | Better to surface them in `focal pm status` as unplanned than to silently drop them |
| `iterations: []` in bootstrapped state | Adopt is about capturing *what exists*; scheduling is a separate concern (`focal pm plan`) |
| Merge, don't overwrite, if state exists | Preserves manually entered SP/iteration data already in the cache |

## Impact

| Area | Impact | Notes |
|------|--------|-------|
| Public API / interfaces | Additive | New `focal pm adopt` command; no existing commands changed |
| Data / schema migration | None | Writes same `focal-state.json` format as existing commands |
| Existing functionality | None | `focal pm init` unchanged; adopt is a parallel onboarding path |
| Performance | Additive | One extra GitHub API call per issue for sub-issue lookup |
| Security | None | |
| Dependencies | None | |
| Other components / services | None | |

## Alternatives considered

| Alternative | Why rejected |
|-------------|-------------|
| Extend `focal pm init` with a `--from-existing` flag | `init` sets up repo structure (templates, labels); adopt is purely a state-bootstrap operation — different concerns, cleaner as a separate command |
| Require issues to be pre-formatted before adopting | Defeats the purpose — the whole point is to handle messy existing state |
| Interactive wizard per issue | Too slow for large backlogs; report-then-confirm is faster and safer |

## Open questions

- [ ] **Q1** — When `--normalise` edits issue bodies to add SP, should it
  append to the existing body or insert a structured table at the top?
  Top is more visible but riskier to existing formatting.
  *(owner: @leninmehedy, due: 2026-06-02)*

- [ ] **Q2** — Should adopt also scan *closed* issues? Useful for
  projects where some stories are already done, but risks polluting the
  active backlog with completed work.
  *(owner: @leninmehedy, due: 2026-06-02)*

- [ ] **Q3** — How to handle a repo where `focal pm init` has already
  run but no `epic-create` has been called? The state file exists but
  is empty. Currently: merge logic treats this as a fresh adoption.
  *(owner: @leninmehedy, due: 2026-06-02)*

## Breakdown hint

Epic: Adopt existing project into Focal PM management (`focal pm adopt`) (~34 SP)
  - Story: Document Focal issue format standard — label, title, body table, sub-issue rules (2 SP)
  - Story: Extend gh.py — issues_by_label(), issue_sub_issues(), project_field_value() (3 SP)
  - Story: Implement sp_extractor.py — extract SP from title, body table, project field (5 SP)
  - Story: Implement hierarchy_resolver.py — sub-issues API, body mentions, title prefix inference (5 SP)
  - Story: Implement state bootstrap — map discovered issues to focal-state.json format (5 SP)
  - Story: Implement adoption report renderer — Rich terminal output with warnings (3 SP)
  - Story: Wire up focal pm adopt CLI command with label mapping flags (3 SP)
  - Story: Implement --apply flag — write state cache + create docs/focal/ structure if missing (3 SP)
  - Story: Implement --normalise flag — re-label issues, move SP from title to body, create sub-issue links (5 SP)

## References

- `focal/pm/pm_state.py` — state cache format this command writes
- `focal/pm/init_cmd.py` — repo bootstrap (complementary, not replaced)
- `focal/gh.py` — GitHub API wrapper to extend
- [D001 — What-if impact assessment](D001-what-if-impact-assessment.md)
- GitHub sub-issues API: `POST /repos/{owner}/{repo}/issues/{issue_number}/sub_issues`
