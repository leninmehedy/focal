---
id: D003
title: Focal MCP server — first-class AI agent integration
author: @leninmehedy
status: Draft
epic:
created: 2026-05-20
updated: 2026-05-20
relates-to: D001, D002
---

# D003 — Focal MCP server

## Abstract

Focal currently integrates with AI agents through `AGENTS.md` — a markdown file
agents read to learn how to construct shell commands. This works but is fragile:
agents parse text, construct command strings, and interpret terminal output. This
design proposes `focal mcp serve` — a local MCP (Model Context Protocol) server
that exposes Focal's PM commands as typed, callable tools. Agents call functions
directly with structured inputs and receive structured outputs, with no shell
command construction and no output parsing required.

## Problem

The current AGENTS.md approach has three failure modes:

1. **Command construction errors** — the agent reads documentation and builds a
   shell command string. If the syntax is wrong, the command fails. The agent then
   tries to recover by re-reading docs and retrying — a slow, unreliable loop.

2. **Output parsing** — agents receive raw terminal output (Rich-formatted tables,
   coloured text, progress lines) and must extract the meaningful data from it.
   This breaks whenever output formatting changes.

3. **No structured feedback** — if `focal pm what-if` shows that three stories
   slip, the agent reads that as text and decides what to do. A typed tool response
   (`{"slipped": ["1.3", "1.5", "2.1"], "capacity_delta": -4}`) lets the agent
   reason over the data directly and chain follow-up actions without re-parsing.

The root cause is that AGENTS.md treats agents like humans reading documentation.
MCP treats agents like code calling a library.

## Goals

- Expose the highest-value Focal PM commands as MCP tools with typed inputs and
  structured JSON outputs
- Users wire it up with a single config entry — no server to provision, no auth,
  no ports
- `focal skill install` automates the config entry for supported agent environments
- All MCP tools remain callable from the CLI as before — MCP is an additional
  interface, not a replacement
- Works with any MCP-compatible agent host (Claude Code, Cursor, and others)

## Non-goals

- Remote/hosted MCP server — this is local-only, stdin/stdout transport
- Replacing the CLI — interactive terminal use is a first-class mode
- Supporting every Focal command via MCP — start with PM commands; board sync
  can follow in a later iteration

## User stories

- As an engineer using Claude Code, I want Focal commands available as native tools
  so the agent can call them without constructing shell strings
- As a maintainer, I want to install the MCP integration in one command so I don't
  have to manually edit config files
- As an agent, I want structured output from what-if scenarios so I can chain
  decisions (e.g. automatically suggest deferring a story after a what-if shows
  a slip) without parsing terminal text
- As an engineer without an AI agent, I want the full interactive CLI to keep
  working exactly as before — MCP is an optional accelerator, not a requirement
- As an agent setting up a new project for a user, I want to drive the entire
  setup sequence — board creation, repo init, first epic, first plan — by
  conversing with the user to collect inputs, then executing non-interactively

## Design

### Transport

MCP supports two transports: stdio (subprocess) and SSE (HTTP). Focal uses
**stdio** — the agent starts `focal mcp serve` as a subprocess, communicates over
stdin/stdout, and the process exits when the session ends. No ports, no hosting,
no auth.

### Implementation

Use the official `mcp` Python SDK (`pip install mcp`). The server is a new
subcommand:

```bash
focal mcp serve
```

Tools are defined as Python functions decorated with `@mcp.tool()`. Each tool
maps to an existing command module — the same logic, different interface:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("focal")

@mcp.tool()
def focal_whatif(
    repo: str,
    pto: list[str] = [],
    inject: list[str] = [],
    reestimate: list[str] = [],
) -> dict:
    """Simulate iteration plan under hypothetical scenarios. Returns per-iteration
    diff with slipped and added stories, capacity changes, and summary counts."""
    from focal.pm.whatif_cmd import _parse_pto, _parse_inject, _parse_reestimate
    from focal.pm.whatif_cmd import _apply_pto, _apply_inject, _apply_reestimate
    from focal.pm.whatif_cmd import _diff_plans
    from focal.pm.plan_helpers import assign_stories_to_iters
    # ... returns structured dict, not rendered output

@mcp.tool()
def focal_plan_status(repo: str, repo_root: str = ".") -> dict:
    """Return current iteration status as structured data."""
    ...

@mcp.tool()
def focal_epic_create(
    repo: str,
    title: str,
    description: str,
    sp: int,
    repo_root: str = ".",
) -> dict:
    """Create a GitHub epic issue and record it in epics.md."""
    ...

@mcp.tool()
def focal_story_create(
    repo: str,
    epic_id: str,
    title: str,
    description: str,
    sp: int,
    repo_root: str = ".",
) -> dict:
    """Create a story linked to an epic."""
    ...

@mcp.tool()
def focal_plan(
    repo: str,
    weeks: int,
    start: str,
    team: str,
    pto: list[str] = [],
    repo_root: str = ".",
) -> dict:
    """Generate iteration-planning.md from local state cache."""
    ...
```

All tools return structured dicts — no Rich formatting, no ANSI codes. The CLI
commands continue to call the same underlying logic and render the output for
humans.

### `focal skill install`

A new subcommand that writes the MCP config entry into the detected agent
environment:

```bash
focal skill install              # auto-detect
focal skill install claude       # Claude Code: writes to .claude/settings.json
focal skill install cursor       # Cursor: writes to .cursor/mcp.json
```

For Claude Code, the entry written to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "focal": {
      "command": "focal",
      "args": ["mcp", "serve"]
    }
  }
}
```

`focal skill install` is idempotent — re-running it is safe.

Human:  "Just automa-saga/logx for now, create a new board, username is leninmehedy"

Agent:  [calls focal_board_setup with all inputs — no prompts, no wizard]
        ✔ Board created
        ✔ ~/.focal/config.json written
```

This pattern — agent converses, human answers once, agent executes non-interactively —
applies to the full setup sequence: board setup → `focal pm init` → first epic →
first plan. The human is never blocked waiting for a wizard prompt; they just
answer the agent's questions in natural language.

The `focal_board_setup` MCP tool signature:

```python
@mcp.tool()
def focal_board_setup(
    owner: str,
    assignee: str,
    repos: list[str],
    create_board: bool = True,
    board_number: int | None = None,  # required if create_board=False
) -> dict:
    """Set up Focal board sync. Creates a GitHub Projects board if create_board
    is True, otherwise uses the supplied board_number. Writes ~/.focal/config.json.
    Returns {board_number, project_id, config_path}."""
    ...
```

### Tool inventory

All commands with agent value are exposed. The full surface:

| Tool | Maps to | Returns |
|---|---|---|
| **Setup** | | |
| `focal_board_setup` | `focal board setup` | `{board_number, project_id, config_path}` |
| `focal_board_sync` | `focal board sync` | `{added, inherited, pushed, stale}` |
| **Repo lifecycle** | | |
| `focal_pm_init` | `focal pm init` | `{repo, files_created, labels_created}` |
| `focal_pm_adopt` | `focal pm adopt` | `{epics, stories, sp_missing, state_path}` |
| **Backlog** | | |
| `focal_epic_create` | `focal pm epic-create` | `{issue_number, epic_id, url}` |
| `focal_story_create` | `focal pm story-create` | `{issue_number, story_id, url}` |
| **Planning** | | |
| `focal_plan` | `focal pm plan` | `{iterations, total_sp, risk_count}` |
| `focal_whatif` | `focal pm what-if` | `{diffs, capacity_notes, summary}` |
| `focal_plan_status` | `focal pm status` | `{iteration, delivered_sp, in_progress, blocked, days_remaining}` |
| **Delivery close** | | |
| `focal_retro` | `focal pm retro` | `{iteration, planned_sp, delivered_sp, carryover_sp}` |
| **Cache** | | |
| `focal_cache_refresh` | `focal cache refresh` | `{epics, stories, last_synced}` |
| `focal_cache_status` | `focal cache status` | `{repos: [{repo, epics, stories, last_synced, status}]}` |
| **Design docs** | | |
| `focal_design_list` | `focal pm design list` | `{designs: [{id, title, status, epic}]}` |

**Why `focal_board_sync` is included:**
Although `focal board sync` normally runs on a scheduler, there is a valid agent
call site: after creating a batch of new issues, the agent can immediately trigger
a sync to pull them onto the personal board without waiting for the next scheduled
run. It is also non-interactive and exits cleanly — a natural fit for a tool call.

**Not exposed:**
`focal pm remove-repo` — administrative housekeeping with no agent-driven use case.
`focal cache refresh-all` — covered by `focal_cache_refresh` per-repo; the
all-repos variant is a maintenance operation better left to the scheduler.

### Non-interactive `focal board setup`

`focal board setup` is currently a wizard — it cannot be driven by an agent.
This design adds a `focal_board_setup` MCP tool and a corresponding
`--non-interactive` CLI mode:

```bash
focal board setup \
  --owner leninmehedy \
  --repos "automa-saga/automa,automa-saga/logx" \
  --create-board \
  --assignee leninmehedy
```

The agent's role is to **collect inputs through conversation first**, then call
the tool once with all required values — never to guess or fill in defaults
silently. The interaction pattern looks like:

```
Human:  "Set up Focal for my new project automa-saga/logx"

Agent:  "I need a few things:
         1. Which GitHub repos should I watch for board sync?
            (I can see automa-saga/logx — any others?)
         2. Do you have an existing GitHub Projects board, or should I create one?
         3. Your GitHub username for assignments?"

## Impact

| Area | Level | Notes |
|---|---|---|
| API / CLI | Additive | New `focal mcp serve` and `focal skill install` subcommands; existing commands unchanged |
| Dependencies | Additive | Adds `mcp` Python SDK as an optional dependency (`pip install focal[mcp]`) |
| Config | Additive | `focal skill install` writes to agent config files; opt-in |
| Security | Needs review | MCP server runs with full local filesystem access; no new attack surface beyond what the CLI already has, but worth confirming |
| Testing | Additive | New test module for MCP tool return shapes |

## Alternatives considered

**Extend AGENTS.md further**
Keep improving the prompt-based approach. Rejected: the failure modes are
structural, not fixable by writing better documentation.

**HTTP/SSE transport instead of stdio**
Would allow the server to run persistently and serve multiple agent sessions.
Rejected for the initial implementation: adds complexity (process management,
port conflicts) with no benefit for the single-user local use case. Can be
added later.

**One MCP tool per CLI flag combination**
E.g. separate `focal_whatif_pto`, `focal_whatif_inject`. Rejected: composable
arguments in a single tool are cleaner and match how agents actually use what-if
(combining multiple scenario flags).

## Open questions

All resolved — none outstanding.

| Question | Resolution |
|---|---|
| Which MCP SDK version to pin? | Pin latest stable at implementation time; managed by dependency bot going forward. |
| Global vs project-local config for `focal skill install`? | **Global** (`~/.claude/settings.json`). Focal is a personal CLI tool — the MCP server is the same binary regardless of repo. |
| Expose `focal_whatif` with `apply: bool`? | **No.** `focal_whatif` is read-only. Applying a plan is a side-effectful action that belongs in the human's hands — agent shows the diff, human decides whether to run `focal pm what-if --apply` themselves. |
| Should `focal_board_setup` create the board or require an existing board number? | **Both, defaulting to create.** `create_board=True` is the happy path for new users; `board_number` is the opt-in for users with an existing board. Agent asks the human which applies before calling the tool. `project` write scope is already required for board sync mutations — no new auth requirement. |

## Breakdown hint

Epic: Focal MCP server (~58 SP)
  - Story: Add mcp dependency as optional extra in pyproject.toml (1 SP)
  - Story: Implement focal mcp serve subcommand with FastMCP scaffold (3 SP)
  - Story: Add --non-interactive mode to focal board setup with all flags (5 SP)
  - Story: Implement focal_board_setup MCP tool (3 SP)
  - Story: Implement focal_board_sync MCP tool (2 SP)
  - Story: Implement focal_pm_init MCP tool (3 SP)
  - Story: Implement focal_pm_adopt MCP tool (3 SP)
  - Story: Implement focal_epic_create MCP tool (3 SP)
  - Story: Implement focal_story_create MCP tool (3 SP)
  - Story: Implement focal_plan MCP tool (5 SP)
  - Story: Implement focal_whatif MCP tool with structured dict output (5 SP)
  - Story: Implement focal_plan_status MCP tool (3 SP)
  - Story: Implement focal_retro MCP tool (5 SP)
  - Story: Implement focal_cache_refresh MCP tool (2 SP)
  - Story: Implement focal_cache_status MCP tool (2 SP)
  - Story: Implement focal_design_list MCP tool (2 SP)
  - Story: Implement focal skill install for Claude Code (3 SP)
  - Story: Implement focal skill install for Cursor (3 SP)
  - Story: Write tests for MCP tool return shapes (3 SP)

## References

- [Model Context Protocol spec](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Claude Code MCP documentation](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [D001 — What-if impact assessment](D001-what-if-impact-assessment.md)
