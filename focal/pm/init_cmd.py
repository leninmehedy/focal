"""focal init — bootstrap a repo with Focal project management structure."""

import subprocess
from pathlib import Path

from rich.console import Console

console = Console()

# Templates live in <focal_root>/templates/ so users can customise them
FOCAL_ROOT = Path(__file__).parent.parent.parent
TEMPLATES_DIR = FOCAL_ROOT / "templates"

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
    _, out, _ = _gh(
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


def _copy_template(src: Path, dest: Path, repo: str) -> None:
    if dest.exists():
        console.print(
            f"  [dim]{dest.relative_to(dest.anchor)} already exists — skipping[/dim]"
        )
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = src.read_text().replace("{repo}", repo)
    dest.write_text(content)
    console.print(f"  [green]✔[/green] {dest}")


def run(repo: str, repo_root: Path) -> None:
    """Bootstrap repo with Focal project management structure."""
    console.print(f"\n[bold cyan]  ◎  Focal Init — {repo}[/bold cyan]\n")

    # ── Labels ────────────────────────────────────────────────────────────────
    console.rule("[bold]Step 1: GitHub labels[/bold]")
    for name, color, desc in LABELS:
        _ensure_label(repo, name, color, desc)

    # ── Issue templates ───────────────────────────────────────────────────────
    console.rule("[bold]Step 2: Issue templates[/bold]")
    for tmpl in (TEMPLATES_DIR / "ISSUE_TEMPLATE").iterdir():
        _copy_template(tmpl, repo_root / ".github" / "ISSUE_TEMPLATE" / tmpl.name, repo)

    # ── Docs scaffold ─────────────────────────────────────────────────────────
    console.rule("[bold]Step 3: Docs scaffold[/bold]")
    for tmpl in ("epics.md", "iteration-planning.md", "retro-log.md"):
        _copy_template(TEMPLATES_DIR / tmpl, repo_root / "docs" / "focal" / tmpl, repo)

    design_dir = repo_root / "docs" / "focal" / "design"
    design_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = design_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
    console.print(f"  [green]✔[/green] {design_dir}/")

    console.print("\n[bold green]Init complete![/bold green]\n")
    console.print("Next steps:")
    console.print(
        f"  Create your first epic:  [bold]python3 focal.py pm epic create --repo {repo}[/bold]"
    )
    console.print(
        "  Commit the scaffold:     [bold]git add docs/focal/ .github/ISSUE_TEMPLATE/ && "
        "git commit -m 'chore: focal init'[/bold]"
    )
    console.print("\nCanonical Status columns for your GitHub Projects board:")
    for col in CANONICAL_STATUS_COLUMNS:
        console.print(f"  {col}")
