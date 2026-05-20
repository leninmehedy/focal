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
    items = json.loads(out).get("items", [])
    if len(items) >= limit:
        import warnings

        warnings.warn(
            f"project_items: fetched {len(items)} items (hit the {limit}-item cap). "
            "Some board statuses may be missing — board sync may be incomplete.",
            stacklevel=2,
        )
    return items


# ── Issue listing ─────────────────────────────────────────────────────────────


def open_assigned_issues(
    repo: str, assignee: str, limit: int = 500, since: str | None = None
) -> list[str]:
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
        "url,updatedAt",
    )
    items: list[dict] = json.loads(out) if out else []
    if since:
        items = [i for i in items if i.get("updatedAt", "") >= since]
    return [i["url"] for i in items if i.get("url")]


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


def issue_state(repo: str, number: int) -> dict:
    """Return {state, assignee} for a single issue (one API call)."""
    out = _run(
        "issue",
        "view",
        str(number),
        "--repo",
        repo,
        "--json",
        "state,assignees",
    )
    data = json.loads(out)
    assignees = [a["login"] for a in data.get("assignees", [])]
    return {
        "state": data["state"].lower(),
        "assignee": assignees[0] if assignees else "",
    }


def issue_states_batch(
    repo: str, numbers: list[int], chunk_size: int = 100
) -> dict[int, dict]:
    """Return {number: {state, assignee}} for many issues using batched GraphQL.

    Fetches up to chunk_size issues per round-trip instead of one call per issue.
    Falls back to individual issue_state() calls if GraphQL fails.
    """
    if not numbers:
        return {}

    owner, name = repo.split("/", 1)
    results: dict[int, dict] = {}

    for i in range(0, len(numbers), chunk_size):
        batch = numbers[i : i + chunk_size]
        aliases = "\n".join(
            f"i{n}: issue(number: {n}) {{ state assignees(first: 1) {{ nodes {{ login }} }} }}"
            for n in batch
        )
        query = f"""
          query {{
            repository(owner: "{owner}", name: "{name}") {{
              {aliases}
            }}
          }}
        """
        try:
            data = _graphql(query)
            repo_data = data.get("data", {}).get("repository", {})
            for n in batch:
                node = repo_data.get(f"i{n}")
                if not node:
                    continue
                assignees = [
                    a["login"] for a in node.get("assignees", {}).get("nodes", [])
                ]
                results[n] = {
                    "state": node["state"].lower(),
                    "assignee": assignees[0] if assignees else "",
                }
        except Exception:
            # Fallback: fetch individually for this chunk
            for n in batch:
                try:
                    results[n] = issue_state(repo, n)
                except RuntimeError:
                    pass

    return results


# ── Board creation ────────────────────────────────────────────────────────────

RECOMMENDED_STATUS_OPTIONS = [
    "🆕 New",
    "📋 Backlog",
    "🔖 Ready",
    "🏗 In progress",
    "✋ Blocked",
    "👀 In review",
    "✅ Done",
]


def owner_id(login: str) -> str:
    """Return the node ID for a user or org login."""
    data = _graphql(f'query {{ user(login: "{login}") {{ id }} }}')
    user = data.get("data", {}).get("user")
    if user:
        return user["id"]
    # Try org
    data = _graphql(f'query {{ organization(login: "{login}") {{ id }} }}')
    return data["data"]["organization"]["id"]


def create_project(login: str, title: str) -> dict:
    """Create a GitHub Projects v2 board. Returns {id, number, url}."""
    oid = owner_id(login)
    data = _graphql(f"""
      mutation {{
        createProjectV2(input: {{
          ownerId: "{oid}"
          title: "{title}"
        }}) {{
          projectV2 {{
            id
            number
            url
          }}
        }}
      }}
    """)
    proj = data["data"]["createProjectV2"]["projectV2"]
    return {"id": proj["id"], "number": proj["number"], "url": proj["url"]}


def get_status_field(project_id: str) -> Optional[dict]:
    """Return the Status single-select field {id, options} for a project."""
    data = _graphql(f"""
      query {{
        node(id: "{project_id}") {{
          ... on ProjectV2 {{
            fields(first: 20) {{
              nodes {{
                ... on ProjectV2SingleSelectField {{
                  id name options {{ id name }}
                }}
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


def set_status_options(project_id: str, field_id: str, options: list[str]) -> None:
    """Replace the options on a Status single-select field."""
    opts_gql = " ".join(f'{{name: "{o}"}}' for o in options)
    _graphql(f"""
      mutation {{
        updateProjectV2Field(input: {{
          projectId: "{project_id}"
          fieldId: "{field_id}"
          singleSelectOptions: [{opts_gql}]
        }}) {{
          projectV2Field {{
            ... on ProjectV2SingleSelectField {{ id name }}
          }}
        }}
      }}
    """)


# ── Adopt helpers ─────────────────────────────────────────────────────────────


def issues_by_label(repo: str, labels: list[str], state: str = "open") -> list[dict]:
    """Return all issues in *repo* that carry any of *labels*.

    Each item includes: number, title, body, labels (list of names),
    assignees (list of logins), state, url.
    """
    owner, name = repo.split("/", 1)
    # GitHub's GraphQL labelFilter returns issues that have ALL listed labels,
    # so we fetch each label separately and deduplicate by issue number.
    seen: dict[int, dict] = {}
    for label in labels:
        query = f"""
          query {{
            repository(owner: "{owner}", name: "{name}") {{
              issues(first: 100, states: [{state.upper()}], labels: ["{label}"]) {{
                nodes {{
                  number title body state url
                  labels(first: 10) {{ nodes {{ name }} }}
                  assignees(first: 5) {{ nodes {{ login }} }}
                }}
              }}
            }}
          }}
        """
        data = _graphql(query)
        nodes = (
            data.get("data", {})
            .get("repository", {})
            .get("issues", {})
            .get("nodes", [])
        )
        for node in nodes:
            num = node["number"]
            if num not in seen:
                seen[num] = {
                    "number": num,
                    "title": node["title"],
                    "body": node.get("body") or "",
                    "state": node["state"].lower(),
                    "url": node["url"],
                    "labels": [lb["name"] for lb in node["labels"]["nodes"]],
                    "assignees": [a["login"] for a in node["assignees"]["nodes"]],
                }
    return sorted(seen.values(), key=lambda i: i["number"])


def issue_sub_issues(repo: str, issue_number: int) -> list[dict]:
    """Return sub-issues of *issue_number* via the GitHub sub-issues REST API.

    Each item: {number, title, state, url}.
    Returns [] for repos/issues with no sub-issues.
    """
    owner, name = repo.split("/", 1)
    try:
        out = _run(
            "api",
            f"repos/{owner}/{name}/issues/{issue_number}/sub_issues",
            "--method",
            "GET",
        )
        items = json.loads(out)
        return [
            {
                "number": i["number"],
                "title": i["title"],
                "state": i["state"].lower(),
                "url": i["html_url"],
            }
            for i in items
        ]
    except RuntimeError:
        return []


def project_field_value(repo: str, issue_number: int, field_name: str) -> Optional[int]:
    """Return the integer value of a GitHub Projects custom field for an issue.

    Searches all projects the issue belongs to for a field named *field_name*.
    Returns None if the field is not found or has no value.
    """
    owner, name = repo.split("/", 1)
    query = f"""
      query {{
        repository(owner: "{owner}", name: "{name}") {{
          issue(number: {issue_number}) {{
            projectItems(first: 10) {{
              nodes {{
                fieldValues(first: 20) {{
                  nodes {{
                    ... on ProjectV2ItemFieldNumberValue {{
                      number
                      field {{ ... on ProjectV2Field {{ name }} }}
                    }}
                    ... on ProjectV2ItemFieldTextValue {{
                      text
                      field {{ ... on ProjectV2Field {{ name }} }}
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
      }}
    """
    try:
        data = _graphql(query)
        project_items = (
            data.get("data", {})
            .get("repository", {})
            .get("issue", {})
            .get("projectItems", {})
            .get("nodes", [])
        )
        for item in project_items:
            for fv in item.get("fieldValues", {}).get("nodes", []):
                fname = (fv.get("field") or {}).get("name", "")
                if fname.lower() == field_name.lower():
                    val = fv.get("number") or fv.get("text")
                    if val is not None:
                        try:
                            return int(val)
                        except (ValueError, TypeError):
                            return None
    except RuntimeError:
        pass
    return None
