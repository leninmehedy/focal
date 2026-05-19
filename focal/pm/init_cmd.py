"""focal init — bootstrap a repo with Focal project management structure."""

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from focal.config import Config

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


def _validate_repo_root(repo: str, repo_root: Path) -> None:
    """Exit with a clear message if repo_root is not a usable local repo directory."""
    import os

    import typer

    if not repo_root.exists() or not repo_root.is_dir():
        console.print(
            f"\n[red]Error:[/red] {repo_root} is not a directory.\n\n"
            f"Run this command from inside your local clone of [bold]{repo}[/bold], "
            "or pass [bold]--repo-root /path/to/clone[/bold]."
        )
        raise typer.Exit(1)

    if not os.access(repo_root, os.W_OK):
        console.print(
            f"\n[red]Error:[/red] No write permission to {repo_root}.\n\n"
            f"Run this command from inside your local clone of [bold]{repo}[/bold], "
            "or pass [bold]--repo-root /path/to/clone[/bold]."
        )
        raise typer.Exit(1)

    if not (repo_root / ".git").exists():
        console.print(
            f"[yellow]Warning:[/yellow] {repo_root} does not appear to be a git repository. "
            "Continuing — commit the scaffold manually when done.\n"
        )


def run(
    repo: str,
    repo_root: Path,
    config: "Config | None" = None,
    config_path: "Path | None" = None,
) -> None:
    """Bootstrap repo with Focal project management structure."""
    console.print(f"\n[bold cyan]  ◎  Focal Init — {repo}[/bold cyan]\n")

    _validate_repo_root(repo, repo_root)

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
    _copy_template(
        TEMPLATES_DIR / "design" / "design-template.md",
        design_dir / "design-template.md",
        repo,
    )
    console.print(f"  [green]✔[/green] {design_dir}/")

    # Register in ~/.focal/config.json pm_repos so cache refresh-all can find this repo
    if config is not None and config_path is not None:
        if config.register_pm_repo(repo, repo_root):
            config.save(config_path)
            console.print(
                "  [green]✔[/green] Registered in config (focal cache refresh-all will include this repo)"
            )

    console.print("\n[bold green]Init complete![/bold green]\n")
    console.print("Next steps:")
    console.print(
        "  1. Write a design doc:   [bold]cp templates/design/design-template.md "
        "docs/focal/design/D001-my-feature.md[/bold]"
    )
    console.print(
        f"  2. Create your first epic:  [bold]focal pm epic-create {repo}[/bold]"
    )
    console.print(
        "  3. Commit the scaffold:  [bold]git add docs/focal/ .github/ISSUE_TEMPLATE/ && "
        "git commit -m 'chore: focal init'[/bold]"
    )
    console.print("\nCanonical Status columns for your GitHub Projects board:")
    for col in CANONICAL_STATUS_COLUMNS:
        console.print(f"  {col}")
