"""Thin wrapper around the gh CLI. All GitHub I/O goes through here."""

import json
import subprocess
from typing import Any, Optional


def _run(*args: str) -> str:
    result = subprocess.run(["gh"] + list(args), capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"gh {args[0]} failed")
    return result.stdout.strip()


def _graphql(query: str) -> Any:
    out = _run("api", "graphql", "-f", f"query={query}")
    return json.loads(out)


# ── Project metadata ──────────────────────────────────────────────────────────


def project_id(number: int, owner: str) -> str:
    out = _run(
        "project",
        "view",
        str(number),
        "--owner",
        owner,
        "--format",
        "json",
        "--jq",
        ".id",
    )
    return out


def project_fields(number: int, owner: str) -> list[dict]:
    out = _run(
        "project", "field-list", str(number), "--owner", owner, "--format", "json"
    )
    return json.loads(out).get("fields", [])


def project_items(number: int, owner: str, limit: int = 500) -> list[dict]:
    out = _run(
        "project",
        "item-list",
        str(number),
        "--owner",
        owner,
        "--limit",
        str(limit),
        "--format",
        "json",
    )
    return json.loads(out).get("items", [])


# ── Issue listing ─────────────────────────────────────────────────────────────


def open_assigned_issues(repo: str, assignee: str, limit: int = 500) -> list[str]:
    out = _run(
        "issue",
        "list",
        "--repo",
        repo,
        "--assignee",
        assignee,
        "--state",
        "open",
        "--limit",
        str(limit),
        "--json",
        "url",
        "--jq",
        ".[].url",
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


# ── Project item mutations ────────────────────────────────────────────────────


def add_item(number: int, owner: str, url: str) -> None:
    _run("project", "item-add", str(number), "--owner", owner, "--url", url)


def set_item_field(
    project_id: str, item_id: str, field_id: str, option_id: str
) -> None:
    _graphql(f"""
      mutation {{
        updateProjectV2ItemFieldValue(input: {{
          projectId: "{project_id}"
          itemId: "{item_id}"
          fieldId: "{field_id}"
          value: {{ singleSelectOptionId: "{option_id}" }}
        }}) {{ projectV2Item {{ id }} }}
      }}
    """)


# ── Issue → origin project items ─────────────────────────────────────────────


def issue_project_items(issue_url: str) -> list[dict]:
    data = _graphql(f"""
      query {{
        resource(url: "{issue_url}") {{
          ... on Issue {{
            projectItems(first: 20) {{
              nodes {{
                id
                project {{ id title }}
                fieldValueByName(name: "Status") {{
                  ... on ProjectV2ItemFieldSingleSelectValue {{ name optionId }}
                }}
              }}
            }}
          }}
        }}
      }}
    """)
    nodes = (
        data.get("data", {})
        .get("resource", {})
        .get("projectItems", {})
        .get("nodes", [])
    )
    return [
        {
            "itemId": n["id"],
            "projectId": n["project"]["id"],
            "projectTitle": n["project"]["title"],
            "status": (n.get("fieldValueByName") or {}).get("name", ""),
        }
        for n in nodes
    ]


def origin_status_field(project_id: str) -> Optional[dict]:
    """Return the Status single-select field (with options) for an origin project."""
    data = _graphql(f"""
      query {{
        node(id: "{project_id}") {{
          ... on ProjectV2 {{
            fields(first: 20) {{
              nodes {{
                ... on ProjectV2SingleSelectField {{ id name options {{ id name }} }}
              }}
            }}
          }}
        }}
      }}
    """)
    for node in data["data"]["node"]["fields"]["nodes"]:
        if node.get("name") == "Status":
            return node
    return None


# ── Issue creation ────────────────────────────────────────────────────────────


def create_issue(
    repo: str, title: str, body: str, labels: list[str], assignee: str
) -> dict:
    """Create an issue and return {number, url, id}."""
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(body)
        body_file = f.name
    try:
        url = _run(
            "issue",
            "create",
            "--repo",
            repo,
            "--title",
            title,
            "--body-file",
            body_file,
            "--label",
            ",".join(labels),
            "--assignee",
            assignee,
        )
    finally:
        os.unlink(body_file)
    # url looks like https://github.com/owner/repo/issues/123
    number = int(url.rstrip("/").split("/")[-1])
    # Fetch integer database ID needed for sub-issues API
    # Fetch integer database ID needed for sub-issues API via GraphQL
    owner, name = repo.split("/")
    data = _graphql(f"""
      query {{
        repository(owner: "{owner}", name: "{name}") {{
          issue(number: {number}) {{ databaseId }}
        }}
      }}
    """)
    db_id = data["data"]["repository"]["issue"]["databaseId"]
    return {"number": number, "url": url, "id": db_id}


def set_item_number_field(
    project_id: str, item_id: str, field_id: str, value: int
) -> None:
    """Set a numeric field (e.g. story points) on a project item."""
    _graphql(f"""
      mutation {{
        updateProjectV2ItemFieldValue(input: {{
          projectId: "{project_id}"
          itemId: "{item_id}"
          fieldId: "{field_id}"
          value: {{ number: {value} }}
        }}) {{ projectV2Item {{ id }} }}
      }}
    """)


def add_item_get_id(number: int, owner: str, url: str) -> str:
    """Add an issue to a project and return the project item ID."""
    out = _run(
        "project",
        "item-add",
        str(number),
        "--owner",
        owner,
        "--url",
        url,
        "--format",
        "json",
        "--jq",
        ".id",
    )
    return out


def link_sub_issue(repo: str, parent_number: int, child_id: int) -> None:
    """Link child issue as a sub-issue of parent using the GitHub sub-issues API."""
    _run(
        "api",
        "--method",
        "POST",
        f"repos/{repo}/issues/{parent_number}/sub_issues",
        "-F",
        f"sub_issue_id={child_id}",
    )
