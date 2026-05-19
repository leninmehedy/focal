---
id: D000          # Auto-assigned: D001, D002, … in sequence
title: <Feature Title>
author: @handle
status: Draft     # Draft | Planned | Active | Done | Archived
created: YYYY-MM-DD
updated: YYYY-MM-DD
relates-to:       # optional: D-IDs or GitHub issue numbers this design connects to
---

# D000 — Feature Title

## Abstract

<!-- 2–4 sentences. What is being built, why, and what problem it solves.
     This is what an AI agent reads first to understand the scope. -->

## Problem

<!-- What is broken, missing, or painful today?
     Be specific — include examples of the failure mode or gap.
     Why does this matter now? -->

## Goals

<!-- What this design achieves. Use a tight bullet list.
     - ✅ Goal 1
     - ✅ Goal 2 -->

## Non-goals

<!-- What this design explicitly does NOT cover. Just as important as goals.
     - ❌ Non-goal 1 (explain why it's out of scope) -->

## User stories

<!-- "As a [user persona], I want [action] so that [outcome]."
     Each story should be independently testable. -->

- As a **[user]**, I want **[action]** so that **[outcome]**.

## Design

<!-- The technical approach. Include as much detail as needed for implementation.
     Subsections are encouraged for complex designs. -->

### Overview

<!-- High-level description of the approach. A diagram or ASCII flow is welcome. -->

### Components

<!-- What components are involved? What does each one do? -->

### Data / schema

<!-- Any new data structures, file formats, API shapes, or schema changes. -->

### Sequence / flow

<!-- Step-by-step description of the happy path.
     Use numbered steps or a sequence diagram. -->

### Key decisions

<!-- Design decisions that were deliberate and non-obvious.
     Format: decision → rationale. -->

| Decision | Rationale |
|----------|-----------|
| <!-- e.g. Use polling not webhooks --> | <!-- e.g. GitHub doesn't emit events for project card moves --> |

## Impact

<!-- For each area, state the impact level and add notes if non-None.
     Impact levels: None · Additive (backwards-compatible) · Breaking · Needs review -->

| Area | Impact | Notes |
|------|--------|-------|
| Public API / interfaces | None | |
| Data / schema migration | None | |
| Existing functionality | None | |
| Performance | None | |
| Security | None | |
| Dependencies | None | |
| Other components / services | None | |

<!-- If any row is non-None, add a sub-section below explaining the change and
     how it will be handled. A Breaking impact requires a migration story. -->

## Alternatives considered

<!-- What else was evaluated and why it was rejected.
     Omitting this section signals the design wasn't compared to alternatives. -->

| Alternative | Why rejected |
|-------------|-------------|
| <!-- option --> | <!-- reason --> |

## Open questions

<!-- Unresolved issues that must be answered before implementation starts.
     Assign an owner and target date if known.
     Remove items as they are resolved — move the decision to Key decisions above. -->

- [ ] **Q1** — <!-- question --> *(owner: @handle, due: YYYY-MM-DD)*

## Breakdown hint

<!-- Plain-English suggestion of how this design maps to epics and stories.
     AI agents use this section when running `focal pm epic-create` and
     `focal pm story-create` to generate the initial backlog.

     Format:
     Epic: <title> (~N SP)
       - Story: <title> (N SP)
       - Story: <title> (N SP)
-->

Epic: <!-- title --> (~N SP)
  - Story: <!-- title --> (N SP)
  - Story: <!-- title --> (N SP)

## References

<!-- URLs, related HIPs, RFCs, prior art, or external docs. -->

-
