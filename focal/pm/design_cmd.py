"""focal pm design — list and inspect design docs in docs/focal/design/."""

from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()

# Lifecycle order — used for sorting and filtering
STATUS_ORDER = ["Draft", "Planned", "Active", "Done", "Archived"]

# Statuses shown in `focal pm status` design summary
ACTIVE_STATUSES = {"Draft", "Planned", "Active"}


def _parse_frontmatter(path: Path) -> dict:
    """Parse YAML-style frontmatter from a markdown file.

    Returns a dict with string values for keys found between the first pair
    of `---` lines.  Returns {} if no frontmatter block is found.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = next((i for i, ln in enumerate(lines[1:], 1) if ln.strip() == "---"), None)
    if end is None:
        return {}
    result: dict = {}
    for line in lines[1:end]:
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.split("#")[0].strip()
    return result


def load_designs(design_dir: Path) -> list[dict]:
    """Return all design docs from *design_dir* sorted by lifecycle then ID.

    Each entry has keys: id, title, status, epic, author, created, updated,
    relates_to, path.
    """
    docs = []
    for p in sorted(design_dir.glob("D[0-9]*.md")):
        fm = _parse_frontmatter(p)
        if not fm:
            continue
        docs.append(
            {
                "id": fm.get("id", p.stem),
                "title": fm.get("title", p.stem),
                "status": fm.get("status", "Draft"),
                "epic": fm.get("epic", ""),
                "author": fm.get("author", ""),
                "created": fm.get("created", ""),
                "updated": fm.get("updated", ""),
                "relates_to": fm.get("relates-to", ""),
                "path": p,
            }
        )
    docs.sort(
        key=lambda d: (
            STATUS_ORDER.index(d["status"]) if d["status"] in STATUS_ORDER else 99,
            d["id"],
        )
    )
    return docs


def run(repo_root: Path, status_filter: str | None = None) -> None:
    """Render design doc list to terminal."""
    design_dir = repo_root / "docs" / "focal" / "design"
    if not design_dir.exists():
        console.print(f"[yellow]No design directory found at {design_dir}[/yellow]")
        return

    docs = load_designs(design_dir)
    if not docs:
        console.print("[dim]No design docs found.[/dim]")
        return

    if status_filter:
        docs = [d for d in docs if d["status"].lower() == status_filter.lower()]
        if not docs:
            console.print(f"[dim]No design docs with status '{status_filter}'.[/dim]")
            return

    # Group by status for display
    by_status: dict[str, list[dict]] = {}
    for d in docs:
        by_status.setdefault(d["status"], []).append(d)

    status_colors = {
        "Draft": "yellow",
        "Planned": "blue",
        "Active": "green",
        "Done": "dim",
        "Archived": "dim",
    }

    console.print()
    console.print("[bold]Design docs[/bold]")

    for status in STATUS_ORDER:
        group = by_status.get(status, [])
        if not group:
            continue
        color = status_colors.get(status, "white")
        table = Table(
            show_header=True,
            header_style="bold",
            box=None,
            pad_edge=False,
            show_edge=False,
        )
        table.add_column("ID", style="bold", width=6)
        table.add_column("Title")
        table.add_column("Epic", width=6)
        table.add_column("Updated", width=12)

        for d in group:
            epic_ref = f"#{d['epic']}" if d["epic"] else "—"
            table.add_row(d["id"], d["title"], epic_ref, d["updated"])

        console.print(f"\n  [{color}]{status}[/{color}]")
        console.print(table)

    console.print()


def summary_lines(repo_root: Path) -> list[str]:
    """Return one-line summaries for active design docs (for pm status footer)."""
    design_dir = repo_root / "docs" / "focal" / "design"
    if not design_dir.exists():
        return []
    docs = [d for d in load_designs(design_dir) if d["status"] in ACTIVE_STATUSES]
    return [f"{d['id']} [{d['status']}] {d['title']}" for d in docs]
