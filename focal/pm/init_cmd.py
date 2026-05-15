"""focal init — bootstrap a repo with Focal project management structure."""

import subprocess
from pathlib import Path

from rich.console import Console

from . import templates

console = Console()

LABELS = [
    ("epic", "5319E7", "Large feature — parent of stories"),
    ("story", "0075CA", "A single deliverable unit of work, child of an epic"),
]

CANONICAL_STATUS_COLUMNS = [
    "🆕 New",
    "📋 Backlog",
    "🔖 Ready",
    "🏗 In progress",
    "✋ Blocked",
    "👀 In review",
    "✅ Done",
]


def _gh(*args: str) -> tuple[int, str, str]:
    result = subprocess.run(["gh"] + list(args), capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _ensure_label(repo: str, name: str, color: str, description: str) -> None:
    rc, _, _ = _gh(
        "label",
        "list",
        "--repo",
        repo,
        "--json",
        "name",
        "--jq",
        f'.[].name | select(. == "{name}")',
    )
    if rc == 0 and name:
        # Check if label already exists
        rc2, out, _ = _gh(
            "label",
            "list",
            "--repo",
            repo,
            "--json",
            "name",
            "--jq",
            f'[.[].name] | contains(["{name}"])',
        )
        if out == "true":
            console.print(f"  [dim]label '{name}' already exists — skipping[/dim]")
            return

    rc, _, err = _gh(
        "label",
        "create",
        name,
        "--repo",
        repo,
        "--color",
        color,
        "--description",
        description,
        "--force",
    )
    if rc != 0:
        console.print(f"  [yellow]⚠[/yellow]  Could not create label '{name}': {err}")
    else:
        console.print(f"  [green]✔[/green] Label '{name}' ready")


def _write_file(path: Path, content: str, overwrite: bool = False) -> bool:
    if path.exists() and not overwrite:
        console.print(f"  [dim]{path} already exists — skipping[/dim]")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    console.print(f"  [green]✔[/green] {path}")
    return True


def run(repo: str, repo_root: Path) -> None:
    """Bootstrap repo with Focal project management structure."""
    console.print(f"\n[bold cyan]  ◎  Focal Init — {repo}[/bold cyan]\n")

    # ── Labels ────────────────────────────────────────────────────────────────
    console.rule("[bold]Step 1: GitHub labels[/bold]")
    for name, color, desc in LABELS:
        _ensure_label(repo, name, color, desc)

    # ── Issue templates ───────────────────────────────────────────────────────
    console.rule("[bold]Step 2: Issue templates[/bold]")
    template_dir = repo_root / ".github" / "ISSUE_TEMPLATE"
    _write_file(template_dir / "epic.md", templates.EPIC_ISSUE_TEMPLATE)
    _write_file(template_dir / "story.md", templates.STORY_ISSUE_TEMPLATE)

    # ── Docs scaffold ─────────────────────────────────────────────────────────
    console.rule("[bold]Step 3: Docs scaffold[/bold]")
    docs_dir = repo_root / "docs"
    _write_file(docs_dir / "epics.md", templates.EPICS_MD.format(repo=repo))
    _write_file(
        docs_dir / "iteration-planning.md",
        templates.ITERATION_PLANNING_MD.format(repo=repo),
    )
    _write_file(docs_dir / "retro-log.md", templates.RETRO_LOG_MD)
    design_dir = docs_dir / "design"
    design_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = design_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
        console.print(f"  [green]✔[/green] {design_dir}/")

    console.print("\n[bold green]Init complete![/bold green]\n")
    console.print("Next steps:")
    console.print(
        "  Create your first epic:  [bold]python3 focal.py epic create --repo "
        + repo
        + "[/bold]"
    )
    console.print(
        "  Commit the scaffold:     [bold]git add docs/ .github/ISSUE_TEMPLATE/ && git commit -m 'chore: focal init'[/bold]"
    )
    console.print("\nCanonical Status columns for your GitHub Projects board:")
    for col in CANONICAL_STATUS_COLUMNS:
        console.print(f"  {col}")
