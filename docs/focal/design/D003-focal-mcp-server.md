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

### Tool inventory (initial scope)

| Tool | Maps to | Returns |
|---|---|---|
| `focal_whatif` | `focal pm what-if` | `{diffs, capacity_notes, summary}` |
| `focal_plan_status` | `focal pm status` | `{iteration, delivered_sp, in_progress, blocked, days_remaining}` |
| `focal_epic_create` | `focal pm epic-create` | `{issue_number, epic_id, url}` |
| `focal_story_create` | `focal pm story-create` | `{issue_number, story_id, url}` |
| `focal_plan` | `focal pm plan` | `{iterations, total_sp, risk_count}` |
| `focal_cache_refresh` | `focal cache refresh` | `{epics, stories, last_synced}` |

Board sync commands (`focal board sync`) are out of scope for the initial
implementation — they have side effects and interactive setup that makes them
less suited to tool-call semantics.

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

| Question | Owner | Due |
|---|---|---|
| Which MCP SDK version to pin? Latest stable at implementation time. | @leninmehedy | Before implementation |
| Should `focal skill install` modify global (`~/.claude/settings.json`) or project-local (`.claude/settings.json`) config? Global makes sense for a CLI tool. | @leninmehedy | Before implementation |
| Do we expose `focal_whatif` with `apply: bool` to allow the agent to commit the simulated plan? Useful but adds risk — agent could write to disk without human review. Default `apply=False`, require explicit opt-in. | @leninmehedy | Before implementation |

## Breakdown hint

Epic: Focal MCP server (~34 SP)
  - Story: Add mcp dependency as optional extra in pyproject.toml (1 SP)
  - Story: Implement focal mcp serve subcommand with FastMCP scaffold (3 SP)
  - Story: Implement focal_whatif MCP tool with structured dict output (5 SP)
  - Story: Implement focal_plan_status MCP tool (3 SP)
  - Story: Implement focal_epic_create MCP tool (3 SP)
  - Story: Implement focal_story_create MCP tool (3 SP)
  - Story: Implement focal_plan MCP tool (5 SP)
  - Story: Implement focal_cache_refresh MCP tool (2 SP)
  - Story: Implement focal skill install for Claude Code (3 SP)
  - Story: Implement focal skill install for Cursor (3 SP)
  - Story: Write tests for MCP tool return shapes (3 SP)

## References

- [Model Context Protocol spec](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Claude Code MCP documentation](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [D001 — What-if impact assessment](D001-what-if-impact-assessment.md)
