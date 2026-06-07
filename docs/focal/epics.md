<!-- focal-managed: do not edit manually — re-rendered from focal-state.json -->
# Epics & Stories

_Last updated: 2026-06-08_

---

## E0 — General Maintenance · [#141](https://github.com/leninmehedy/focal/issues/141) · 10 SP


| Story | GitHub | SP | Status |
|---|---|---|---|
| **0.1** — focal pm status --no-plan: solo/lightweight mode using build-log.md as tracker | [#146](https://github.com/leninmehedy/focal/issues/146) | 5 | 🔄 |
| **0.2** — focal pm triage — list open issues not linked to any epic | [#135](https://github.com/leninmehedy/focal/issues/135) | 3 | 🔄 |
| **0.3** — MCP server: add focal_pm_triage and focal_pm_adopt_plan tools | [#155](https://github.com/leninmehedy/focal/issues/155) | 2 | 🔄 |

---

## E5 — Epic: focal pm adopt-plan: bootstrap a project from a plan doc (EPICS.md) · [#147](https://github.com/leninmehedy/focal/issues/147) · 3 SP


| Story | GitHub | SP | Status |
|---|---|---|---|

---

## E3 — Epic: focal pm adopt — bootstrap Focal PM state from existing repo issues · [#143](https://github.com/leninmehedy/focal/issues/143) · 3 SP


| Story | GitHub | SP | Status |
|---|---|---|---|
| **3.1** — Implement sp_extractor.py — extract SP from title, body table, project field | [#84](https://github.com/leninmehedy/focal/issues/84) | 5 | 🔄 |
| **3.2** — Implement hierarchy_resolver.py — sub-issues API, body mentions, title prefix inference | [#85](https://github.com/leninmehedy/focal/issues/85) | 5 | 🔄 |
| **3.3** — Implement state bootstrap — map discovered issues to focal-state.json format | [#86](https://github.com/leninmehedy/focal/issues/86) | 5 | 🔄 |
| **3.4** — Implement adoption report renderer — Rich terminal output with warnings | [#87](https://github.com/leninmehedy/focal/issues/87) | 3 | 🔄 |
| **3.5** — Wire up focal pm adopt CLI command with label mapping flags | [#88](https://github.com/leninmehedy/focal/issues/88) | 3 | 🔄 |
| **3.6** — Implement --apply flag — write state cache + create docs/focal/ structure if missing | [#89](https://github.com/leninmehedy/focal/issues/89) | 3 | 🔄 |
| **3.7** — Implement --normalise flag — re-label issues, add SP to body, create sub-issue links | [#90](https://github.com/leninmehedy/focal/issues/90) | 5 | 🔄 |
| **3.8** — Document Focal issue format standard — label, title, body table, sub-issue rules | [#91](https://github.com/leninmehedy/focal/issues/91) | 2 | 🔄 |

---

## E4 — Epic: focal pm epic-create --from-design: create epic+stories from design doc breakdown · [#144](https://github.com/leninmehedy/focal/issues/144) · 3 SP


| Story | GitHub | SP | Status |
|---|---|---|---|
| **4.1** — Wire --from-design flag into focal pm epic-create CLI | [#111](https://github.com/leninmehedy/focal/issues/111) | 1 | 🔄 |

---

## E2 — Epic: focal pm what-if — impact assessment for iteration planning · [#142](https://github.com/leninmehedy/focal/issues/142) · 3 SP


| Story | GitHub | SP | Status |
|---|---|---|---|
| **2.1** — Extract shared plan helpers from plan_cmd.py (greedy assign, capacity calc) — D001 | [#70](https://github.com/leninmehedy/focal/issues/70) | 3 | 🔄 |
| **2.2** — Implement iteration_parser.py — parse iteration-planning.md into structured data — D001 | [#71](https://github.com/leninmehedy/focal/issues/71) | 5 | 🔄 |
| **2.3** — Scenario: PTO capacity reduction — subtract leave days from affected person's capacity in overlapping iterations — D001 | [#72](https://github.com/leninmehedy/focal/issues/72) | 5 | 🔄 |
| **2.4** — Scenario: work injection — prepend urgent story to current iteration backlog — D001 | [#73](https://github.com/leninmehedy/focal/issues/73) | 3 | 🔄 |
| **2.5** — Update focal pm init to drop EPICS-template.md and explain plan-doc onboarding path | [#152](https://github.com/leninmehedy/focal/issues/152) | 2 | 🔄 |
| **2.6** — Update AGENTS.md and docs/user-guide.md with adopt-plan workflow | [#153](https://github.com/leninmehedy/focal/issues/153) | 2 | 🔄 |
| **2.7** — Impact report renderer — Rich terminal output with before/after panels, slipped stories, projected completion shift — D001 | [#76](https://github.com/leninmehedy/focal/issues/76) | 5 | 🔄 |
| **2.8** — Wire up focal pm what-if CLI command with --pto, --inject, --reestimate flags — D001 | [#77](https://github.com/leninmehedy/focal/issues/77) | 3 | 🔄 |
| **2.9** — Add --apply flag to write updated iteration-planning.md — D001 | [#78](https://github.com/leninmehedy/focal/issues/78) | 3 | 🔄 |

---
