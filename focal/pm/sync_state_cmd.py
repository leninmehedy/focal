"""focal pm sync-state — refresh local state cache from GitHub."""

from pathlib import Path

from rich.console import Console

from . import pm_state

console = Console()


def run(repo: str, repo_root: Path, config: dict) -> None:
    """Re-fetch all epic/story status from GitHub and update local cache."""
    console.print(f"\n[bold cyan]  ◎  Focal — sync-state ({repo})[/bold cyan]\n")

    state = pm_state.load(repo_root)
    if not state["epics"]:
        console.print(
            "[yellow]No epics in local state. Run [bold]focal pm epic-create[/bold] first.[/yellow]"
        )
        return

    console.print(f"Refreshing {len(state['epics'])} epics from GitHub...")
    state = pm_state.refresh_from_github(repo_root, repo, config)

    total_stories = sum(len(e.get("stories", [])) for e in state["epics"])
    console.print(
        f"  [green]✔[/green] Synced {len(state['epics'])} epics, "
        f"{total_stories} stories"
    )
    console.print(f"  [green]✔[/green] Last synced: {state['last_synced']}")
