---
id: D004
title: "focal pm adopt-plan: bootstrap a project from a plan doc (plan.md)"
author: @leninmehedy
status: Active
epic: 147
created: 2026-06-08
updated: 2026-06-08
relates-to: D002
---

# D004 — focal pm adopt-plan: bootstrap a project from a plan doc (plan.md)

## Abstract

A developer (or their AI agent) writes `docs/focal/plan.md` — a structured
plan doc with a release ladder, dependency graph, and epic/story tables.
`focal pm adopt-plan` reads that file, creates GitHub issues for every epic
and story, writes issue links back into the same file, and bootstraps the
focal state cache. After that, focal keeps the file updated going forward
via `epic-create`, `story-create`, and `cache refresh`. The plan doc and the
tracking index are the same file — two phases, one artifact.

---

## Problem

Developers already write structured plans before touching GitHub. These plans
exist as markdown files (`docs/focal/plan.md`, `plan.md`, etc.) and often
contain more design context than a GitHub issue — release ladder, dependency
graph, rationale per epic. The current focal workflow discards this artifact:
`focal pm init` drops a near-empty `plan.md` scaffold, and `focal pm adopt`
reads labelled GitHub issues (which may not exist yet). There is no path from
"I have a plan doc" to "focal is managing this project."

---

## Proposed solution

### One file, two phases

```
Phase 1 — Plan (human/agent-written)
  docs/focal/plan.md
    Release ladder table
    Dependency graph
    ## E1 — Title · ~N SP
    prose description
    | Story | SP | Notes |

Phase 2 — Active (focal-maintained)
  adopt-plan reads plan.md, creates GitHub issues,
  writes back issue links into the same file.
  epic-create / story-create append new sections.
  cache refresh updates status markers.
```

After Phase 2 begins, the file looks identical to Phase 1 except each
heading and story row gains an issue link:

```markdown
## E2 — Board sync non-interactive flags · [#140](url) · 7 SP
## E3 — focal pm adopt-plan · [#147](url) · 22 SP

| Story | GitHub | SP | Notes |
| **3.1** — Define canonical plan.md format | [#148](url) | 2 | |
```

### Canonical `docs/focal/plan.md` format

`focal pm init` will drop this richer template (replacing the current thin
scaffold). Sections focal **reads**: Release ladder, epic headings, story
tables. Sections focal **never writes**: prose descriptions, dependency
graph, notes columns.

```markdown
# Epics & Stories

Repository: `owner/repo`

---

## Release ladder

| Epic | Version | Status | Gate |
|---|---|---|---|
| E1 — General Maintenance | ongoing | 🔄 Open | — |
| E2 — Board sync setup | v0.1 | ✅ Done | board setup non-interactive |
| E3 — adopt-plan | v0.2 | 🔄 Next | E2 stable |

## Dependency graph

```
E1 — General Maintenance (permanent, parallel to all)
E2 — Board sync setup ✅
    └── E3 — adopt-plan ← CURRENT
        └── E4 — --from-design flag
```

---

## E1 — General Maintenance · [#141](url) · ongoing

Catch-all for bugs and unplanned work. Always open.

| Story | GitHub | SP | Notes |
|---|---|---|---|
| **1.1** — focal board setup non-interactive flags | [#137](url) | 5 | ✅ merged #140 |
| **1.2** — focal pm init missing board-setup hint | [#138](url) | 2 | ✅ merged #140 |
| **1.3** — focal pm status --no-plan solo mode | [#146](url) | 5 | |

---

## E2 — focal pm adopt-plan · [#147](url) · 22 SP

Bootstrap a project from a plan doc rather than from existing labelled issues.

| Story | GitHub | SP | Notes |
|---|---|---|---|
| **2.1** — Define canonical plan.md format + update focal pm init template | [#148](url) | 2 | |
| **2.2** — Implement plan_doc_parser.py | [#149](url) | 5 | |
| **2.3** — Implement adopt_plan_cmd.py | [#150](url) | 8 | |
| **2.4** — Wire focal pm adopt-plan CLI | [#151](url) | 3 | |
| **2.5** — Update focal pm init to reference adopt-plan onboarding | [#152](url) | 2 | |
| **2.6** — Update AGENTS.md + user-guide | [#153](url) | 2 | |

---

## Story point legend

| SP | Size |
|---|---|
| 1 | Hours |
| 2 | Half day |
| 3 | 1 day |
| 5 | 2–3 days |
| 8 | ~1 week |
```

---

## Parser design — `focal/pm/plan_doc_parser.py`

### What the parser reads

| Element | Pattern | Focal action |
|---|---|---|
| Epic heading | `## EN — Title · [optional link] · N SP` | create/update epic |
| Epic heading (no issue yet) | `## EN — Title · ~N SP` | create issue, write link back |
| Story table row | `\| **N.M** — Title \| [optional link] \| N \|` | create/update story |
| Story row (no issue yet) | `\| **N.M** — Title \| N \| notes \|` | create issue, write link back |
| Release ladder table | `## Release ladder` section | read-only — status reference |
| Dependency graph | ` ``` ` block after `## Dependency graph` | read-only — never written |
| Prose paragraphs | any line not matching the above | read-only — never written |

### Parser output (structured data)

```python
@dataclass
class ParsedStory:
    local_id: str          # "2.1"
    title: str             # "Implement plan_doc_parser.py"
    sp: int | None
    notes: str             # raw notes column content
    issue_number: int | None  # None if not yet created
    issue_url: str | None

@dataclass
class ParsedEpic:
    local_id: str          # "E2"
    title: str             # "focal pm adopt-plan"
    sp: int | None
    issue_number: int | None
    issue_url: str | None
    stories: list[ParsedStory]

@dataclass
class ParsedPlanDoc:
    repo: str | None       # from header line "Repository: `owner/repo`"
    epics: list[ParsedEpic]
```

### Heading regex

```python
# Matches: ## E2 — Title · [#147](url) · 22 SP
#          ## E2 — Title · ~22 SP
EPIC_RE = re.compile(
    r"^## (E\w+) — (.+?) · "
    r"(?:\[#(\d+)\]\(([^)]+)\) · )?"   # optional issue link
    r"~?(\d+) SP",
    re.MULTILINE,
)

# Matches: | **2.1** — Title | [#148](url) | 5 | notes |
#          | **2.1** — Title | 5 | notes |
STORY_RE = re.compile(
    r"^\| \*\*(\d+\.\w+)\*\* — (.+?) \| "
    r"(?:\[#(\d+)\]\(([^)]+)\) \| )?"  # optional issue link
    r"(\d+) \|",
    re.MULTILINE,
)
```

### Surgical writer — patching issue links without touching prose

The writer never re-renders whole sections. It makes targeted line-level
substitutions on the raw file text:

```python
def patch_epic_link(text: str, local_id: str, number: int, url: str) -> str:
    """Replace `## E2 — Title · ~21 SP` with `## E2 — Title · [#147](url) · 21 SP`."""
    return re.sub(
        rf"^(## {re.escape(local_id)} — .+?) · ~?(\d+ SP)",
        rf"\1 · [#{number}]({url}) · \2",
        text,
        flags=re.MULTILINE,
    )

def patch_story_link(text: str, local_id: str, number: int, url: str) -> str:
    """Replace `| **2.1** — Title | 5 |` with `| **2.1** — Title | [#N](url) | 5 |`."""
    return re.sub(
        rf"^(\| \*\*{re.escape(local_id)}\*\* — .+?) \| (\d+ \|)",
        rf"\1 | [#{number}]({url}) | \2",
        text,
        flags=re.MULTILINE,
    )
```

Rules the writer follows:
- Only substitutes lines that match the exact pattern above
- Never rewrites prose paragraphs, dependency graphs, or release ladder rows
- After patching, writes the whole file back atomically (temp file + rename)
- Idempotent — if the link is already present, the regex won't match, nothing changes

---

## `adopt_plan_cmd.py` — execution flow

```
1. parse_plan_doc(epics_md_path)
   → ParsedPlanDoc (epics + stories, issue numbers where already present)

2. for each epic with no issue_number:
     gh.create_issue(title, body=description, labels=["epic"])
     patch_epic_link(epics_md, epic.local_id, issue.number, issue.url)

3. for each story with no issue_number:
     gh.create_issue(title, body=f"Part of #{epic.issue_number}\n\n| SP | {sp} |\n|---|---|",
                     labels=["story"])
     gh.link_sub_issue(epic.issue_number, story_db_id)
     patch_story_link(epics_md, story.local_id, issue.number, issue.url)

4. write patched epics_md back to disk

5. bootstrap focal-state.json from parsed + newly created issues

6. if no focal pm init yet: run init_cmd.run() (labels, templates, E0)
```

Step 2–4 are idempotent: re-running `adopt-plan` on a file that already has
links skips creation and only fills in any gaps.

---

## `focal pm init` changes (story #152)

After `adopt-plan` exists, `focal pm init` next-steps become:

```
Next steps:
  1. Write your plan:     edit docs/focal/plan.md
  2. Adopt the plan:      focal pm adopt-plan owner/repo
  3. Commit the scaffold: git add docs/focal/ .github/ && git commit -m 'chore: focal init'
```

The old "write a design doc → epic-create --from-design" path stays valid
for adding new epics *within* an already-managed project; `adopt-plan` is the
project-level onboarding path.

---

## What focal never touches in `plan.md`

| Section | Reason |
|---|---|
| Release ladder table | Human decision — version targets, gates, status |
| Dependency graph code block | Narrative structure — wrong to auto-update |
| Prose paragraphs under epic headings | Context and rationale — human-written |
| Notes column in story tables | Free-form field — focal only reads SP column |

---

## Acceptance criteria

- [ ] `focal pm adopt-plan owner/repo` dry-runs by default, showing what would be created
- [ ] `--apply` executes: creates issues, patches links, bootstraps state
- [ ] Idempotent: re-running with `--apply` on an already-adopted file is a no-op
- [ ] Prose, dependency graph, release ladder rows are never modified
- [ ] `focal pm epic-create` and `story-create` append new sections in the same format
- [ ] `focal pm init` drops the richer plan.md template with Release ladder + Dependency graph sections
- [ ] `focal pm init` next-steps mention `adopt-plan` as the recommended first step
- [ ] AGENTS.md updated with the brainstorm → plan.md → adopt-plan → board-sync loop
- [ ] `docs/testing-guide.md` updated with AP1–AP8 test cases
