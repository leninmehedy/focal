"""Static templates for Focal project management docs and GitHub config files."""

EPIC_ISSUE_TEMPLATE = """\
---
name: Epic
about: Large feature — parent of stories
title: "Epic: "
labels: epic
assignees: ''
---

## Vision

<!-- What problem does this epic solve? What does success look like? -->

## Stories

<!-- Stories will be added here as sub-issues -->

## Acceptance criteria

<!-- What must be true for this epic to be considered done? -->
"""

STORY_ISSUE_TEMPLATE = """\
---
name: Story
about: A single deliverable unit of work, child of an epic
title: ""
labels: story
assignees: ''
---

Part of epic #<!-- epic number -->.

<!-- Describe what needs to be done and why. Keep it to one deliverable outcome. -->

**Estimated:** <!-- N SP -->
"""

EPICS_MD = """\
# Epics & Stories

Repository: `{repo}` | Project: [{repo}](https://github.com/{repo})

---

<!-- Add epics below using the format produced by `focal epic create` -->

<!--
## E1 — Epic Title · #issue · N SP

Description of the epic.

| Story | GitHub | SP |
|---|---|---|
| **1.1** — Story title | [#issue](https://github.com/{repo}/issues/N) | N |
-->
"""

ITERATION_PLANNING_MD = """\
# Iteration Planning

Milestone: `<!-- milestone name -->`
Repo: `{repo}`
Total scope: **<!-- N SP -->** across <!-- N epics --> and <!-- N stories -->

---

## Team

| Name | GitHub | Focus Area |
|------|--------|------------|
| <!-- name --> | @<!-- handle --> | <!-- area --> |

### Effective per-track capacity (SP/iteration)

| Track | Owner | SP/iter |
|-------|-------|---------|
| <!-- track --> | <!-- owner --> | <!-- N --> |

---

## Iteration Setup

| Parameter | Value |
|-----------|-------|
| Length | 2 weeks |
| Start date | <!-- YYYY-MM-DD --> |
| Allocation | <!-- e.g. 80-20 --> |
| Effective capacity | <!-- N SP/iter --> |
| Team velocity | <!-- ~N SP/iteration --> |
| Projected end | <!-- date --> |

---

## Capacity & PTO

| Engineer | Dates | Working days affected |
|----------|-------|-----------------------|
| <!-- name --> | <!-- dates --> | <!-- N days (IN) --> |

### Iteration Capacity (SP)

| # | Dates | Total SP | Notes |
|---|-------|----------|-------|
| I1 | <!-- dates --> | **0** | |

---

## Risks

| Severity | Risk | Mitigation |
|----------|------|------------|
| 🟡 Medium | <!-- risk --> | <!-- mitigation --> |

---

## Iteration Schedule

| Iter | Dates | Cap | Work |
|------|-------|-----|------|
| **I1** | <!-- dates --> | <!-- N --> | <!-- stories --> |
"""

RETRO_LOG_MD = """\
# Iteration Retrospective Log

Slip reason codes: `SCOPE` · `BLOCKED` · `LEAVE` · `TRAVEL` · `CARRY` · `REPRIORITY`

---

<!-- Iterations are appended below by `focal retro` -->

<!--
## I1 - <start date> (<date range>)

### Planned
- @handle: #N story title (N SP)

### Delivered
- @handle: #N

### Velocity
- Planned: N SP · Delivered: N SP · Carry-over: N SP

### Slip Reasons
<!-- Format: #issue — CODE — reason -->

### Notes

---
-->

## Cumulative Velocity

| Iteration | Planned SP | Delivered SP | Cumulative Delivered | Cumulative Planned |
|---|---|---|---|---|
| <!-- I1 --> | <!-- N --> | <!-- N --> | <!-- N --> | <!-- N --> |
"""
