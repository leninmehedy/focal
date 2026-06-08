# How to Run the Focal Test Suite (Automated)

This is the runbook for re-running the full automated test suite.
It is written for an AI agent (Claude Code) but a human can follow it too.

---

## Prerequisites

Before starting, verify:

```bash
python3 --version      # 3.10+
gh --version           # 2.x+
gh auth status         # must show repo + project scopes
focal --version        # confirm editable install is active
```

If `focal` is not installed from source:

```bash
cd /path/to/focal
pip3 install -e .
```

The `gh` token needs the `project` scope:

```bash
gh auth refresh -s project
```

---

## Setup

### 1. Branch

Always run on a dated branch — never on `main`:

```bash
git checkout main && git pull
git checkout -b test/automated-run-YYYY-MM-DD
```

### 2. Copy the report template

```bash
cp docs/test-runs/2026-06-08.md docs/test-runs/YYYY-MM-DD.md
```

Open it and update the header fields:
- `Version under test` — run `focal --version`
- `Commit` — run `git log --oneline -1`
- `Started` — today's date
- Reset all result cells from previous run to `—`

### 3. Create the private test repo

```bash
gh repo create leninmehedy/focal-test-YYYY-MM-DD \
  --private \
  --description "Focal automated test repo — YYYY-MM-DD"

# Seed a README so the repo has a default branch
gh api repos/leninmehedy/focal-test-YYYY-MM-DD/contents/README.md \
  --method PUT \
  --field message="chore: init test repo" \
  --field content="$(echo '# focal-test\nAutomated test repo.' | base64)"
```

### 4. Configure permissions

The project `.claude/settings.json` already has the right allowlist scoped to this
directory. If running a fresh session, restart Claude Code from the focal repo root
so it picks up the settings file.

---

## Running the Tests

Work through `docs/testing-guide.md` section by section.
The test IDs (I3, BS1, PI1, etc.) match the rows in the report template.

### Key variables to substitute

| Placeholder | Replace with |
|---|---|
| `YYYY-MM-DD` | today's date, e.g. `2026-06-08` |
| `leninmehedy/focal-test-YYYY-MM-DD` | your test repo name |
| `/tmp/focal-test` | local clone path (see below) |

### Clone the test repo locally

Most PM commands need `--repo-root`. Clone once at the start:

```bash
gh repo clone leninmehedy/focal-test-YYYY-MM-DD /tmp/focal-test
```

### Back up your live config before setup tests

```bash
cp ~/.focal/config.json ~/.focal/config.json.bak
```

Restore after reset tests:

```bash
cp ~/.focal/config.json.bak ~/.focal/config.json
```

---

## Section-by-section notes

### Installation (I3–I5)
Smoke tests only. Just run the three commands and check output.

### Setup (S3, S5, S7, S9–S12)
- Use `--create-board` for S9 (creates a new Projects board)
- Use `--use-board --use-board-number N` for S10 (N = board number from S9)
- After S10 verify `~/.focal/config.json` has the right `board_number`

### Board Sync (BS1, BS3, BS6, BS7, BS10)
- Create a test issue first: `gh issue create --repo ... --assignee leninmehedy --title "Test issue"`
- BS3: run sync twice and check the log for `(incremental)` — **known BUG-1**: second run incorrectly marks issue stale
- BS6: close the issue, then sync — check the log for `Stale (closed/unassigned)` ✅ and `No personal board option for '✅ Done'` ⚠ (BUG-2)
- BS7: temporarily move config aside: `mv ~/.focal/config.json ~/.focal/config.json.tmp && focal board sync && mv *.tmp *.json`

### PM Init (PI1–PI10)
- Run `focal pm init leninmehedy/focal-test-YYYY-MM-DD --repo-root /tmp/focal-test`
- PI7/PI8: remove config first, run init, check for ⚠ banner and step 0
- PI10: **known BUG-3** — `focal pm init nonexistent/norepo` silently succeeds

### PM Adopt-plan (AP1–AP8)
Use this exact `plan.md` format (the parser is strict):

```markdown
## E0 — General Maintenance · ~ongoing

| Story | SP | Notes |
|---|---|---|

---

## E1 — My First Epic · ~8 SP

Description here.

| Story | SP | Notes |
|---|---|---|
| **1.1** — First story title | 3 | |
| **1.2** — Second story title | 5 | |
```

- AP2/AP3/AP4: **known BUG-4** — stories not created on first `--apply`; run `--apply` twice

### PM Plan (PL1–PL5)
`focal pm plan` always prompts `Any PTO or travel?` even with all flags. Pipe the answer:

```bash
echo "n" | focal pm plan owner/repo --weeks 2 --start YYYY-MM-DD --team "handle:8" ...
```

- PL3: **known BUG-5** — `--goals` flag silently ignored in output

### PM Retro (RE1–RE6)
`focal pm retro` prompts for slip reason (and optional note) per carry-over story
even with all flags. Pipe blank lines to accept CARRY defaults:

```bash
# 2 inputs per story (slip code + note), N stories = 2N newlines
printf "\n\n\n\n" | focal pm retro owner/repo --iteration I1 --goal-met \
  --went-well "..." --to-improve "..." --repo-root /tmp/focal-test
```

Count carry-over stories from the output and adjust `\n` count accordingly.

### PM Velocity (V1–V4)
- V1/V2: **known BUG-6** — velocity parser returns all zeros and reads comment block

### What-if (WI1–WI9)
- WI3/WI4: `--inject` and `--reestimate` may show "No stories affected" even when
  scenarios should cause ripple — verify the plan has stories assigned to iterations first

### Cache (CR1–CR4, CA1–CA5, CS1–CS4)
All non-interactive. No known issues.

### Solo mode (S1–S14, ER1–ER4, SR1–SR5)
Use a separate temp dir for solo tests to avoid collision with PM test state:

```bash
mkdir -p /tmp/focal-solo-test
focal pm solo init leninmehedy/focal-test-YYYY-MM-DD --repo-root /tmp/focal-solo-test
```

### MCP (MCP1, MCP4, MCP5)
- MCP1: **known** — exits with code 1 on successful install (cosmetic)

---

## After the run

### 1. Fill in the summary table

Count pass/fail/partial/skip per group and update the Summary table at the top.

### 2. File new bugs

For any new failures not already in the known bugs list, create stories under E0:

```bash
focal pm story-create leninmehedy/focal \
  --epic E0 \
  --title "Short bug title" \
  --description "Steps to reproduce, expected vs actual, test ID" \
  --sp 3 \
  --repo-root /path/to/focal
```

### 3. Commit and push

```bash
git add docs/test-runs/YYYY-MM-DD.md
git commit -m "docs: add automated test run report for YYYY-MM-DD"
git push -u origin test/automated-run-YYYY-MM-DD
```

### 4. Delete the test repo

The test repo requires `delete_repo` scope to delete via CLI:

```bash
gh auth refresh -s delete_repo
gh repo delete leninmehedy/focal-test-YYYY-MM-DD --yes
```

Or delete it manually at:
`https://github.com/leninmehedy/focal-test-YYYY-MM-DD/settings` → Danger Zone → Delete this repository

### 5. Restore your live config

```bash
cp ~/.focal/config.json.bak ~/.focal/config.json
```

---

## Known bugs (as of 2026-06-08)

These are expected failures — do not file duplicates. Check if they are fixed.

| Bug | Test | Issue | Description |
|---|---|---|---|
| BUG-1 | BS3 | [#161](https://github.com/leninmehedy/focal/issues/161) | Incremental sync falsely marks valid issues as stale |
| BUG-2 | BS6 | [#162](https://github.com/leninmehedy/focal/issues/162) | `--use-board` writes wrong `done_status` |
| BUG-3 | PI10 | [#163](https://github.com/leninmehedy/focal/issues/163) | `pm init` silently succeeds on non-existent repo |
| BUG-4 | AP2–AP4 | [#164](https://github.com/leninmehedy/focal/issues/164) | `adopt-plan` stories not created on first `--apply` |
| BUG-5 | PL3 | [#165](https://github.com/leninmehedy/focal/issues/165) | `--goals` flag silently ignored in plan doc |
| BUG-6 | V1–V2 | [#166](https://github.com/leninmehedy/focal/issues/166) | Velocity parser returns all zeros; reads comment block |

---

## Prompting an agent to run this

Paste this into a new Claude Code session opened from the focal repo root:

```
Read docs/test-runs/HOW-TO-RUN.md and docs/testing-guide.md.
Run the full focal test suite:
- Create a dated test branch
- Copy docs/test-runs/2026-06-08.md as the report template for today
- Create private test repo leninmehedy/focal-test-<today's date>
- Run all automatable tests section by section
- Fill in the report as you go
- File new bugs with focal pm story-create under E0
- Commit the report and push the branch
- Delete the test repo when done
```
