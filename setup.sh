#!/usr/bin/env bash
# setup.sh — Interactive setup wizard for sync-gh-board.
#
# What it does:
#   1. Checks prerequisites (gh CLI, authentication, scopes)
#   2. Asks for your personal board URL and assignee username
#   3. Lets you choose repos to sync (manual list / interactive select / full scan)
#   4. Inspects Status columns in each repo's projects vs your personal board
#   5. Reports mismatches; offers to fix them or generates a status_map.json fallback
#   6. Writes config.sh ready for sync.sh to consume
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.sh"
STATUS_MAP_FILE="$SCRIPT_DIR/status_map.json"

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}ℹ ${RESET}$*"; }
success() { echo -e "${GREEN}✔ ${RESET}$*"; }
warn()    { echo -e "${YELLOW}⚠ ${RESET}$*"; }
error()   { echo -e "${RED}✖ ${RESET}$*" >&2; }
header()  { echo -e "\n${BOLD}$*${RESET}"; echo "$(echo "$*" | sed 's/./-/g')"; }
prompt()  { echo -en "${BOLD}$* ${RESET}"; }

# ── Step 1: Prerequisites ─────────────────────────────────────────────────────
header "Step 1: Checking prerequisites"

if ! command -v gh &>/dev/null; then
  error "GitHub CLI (gh) is not installed."
  echo "  Install it from: https://cli.github.com"
  exit 1
fi
success "gh CLI found: $(gh --version | head -1)"

if ! gh auth status &>/dev/null; then
  error "Not authenticated with gh. Run: gh auth login"
  exit 1
fi

GH_USER=$(gh api user --jq '.login' 2>/dev/null)
success "Authenticated as: $GH_USER"

# Check required scopes
SCOPES=$(gh auth status 2>&1 | grep -o "Token scopes:.*" | head -1 || true)
info "Token scopes: ${SCOPES#Token scopes: }"

missing_scopes=()
echo "$SCOPES" | grep -q "repo"    || missing_scopes+=("repo")
echo "$SCOPES" | grep -q "project" || missing_scopes+=("project")

if [[ ${#missing_scopes[@]} -gt 0 ]]; then
  warn "Missing required scopes: ${missing_scopes[*]}"
  echo "  Re-authenticate with: gh auth login --scopes repo,project"
  prompt "Continue anyway? [y/N]"
  read -r ans; [[ "$ans" =~ ^[Yy]$ ]] || exit 1
else
  success "Required scopes present (repo, project)"
fi

# ── Step 2: Personal board ────────────────────────────────────────────────────
header "Step 2: Personal board"

prompt "Your GitHub username [default: $GH_USER]:"
read -r BOARD_OWNER
BOARD_OWNER="${BOARD_OWNER:-$GH_USER}"
ASSIGNEE="$BOARD_OWNER"

echo ""
info "Enter your personal GitHub Projects board URL or number."
info "Example: https://github.com/users/you/projects/3  or just: 3"
prompt "Board URL or number:"
read -r BOARD_INPUT

# Extract number from URL or use directly
if [[ "$BOARD_INPUT" =~ /projects/([0-9]+) ]]; then
  BOARD_NUMBER="${BASH_REMATCH[1]}"
else
  BOARD_NUMBER="${BOARD_INPUT//[^0-9]/}"
fi

if [[ -z "$BOARD_NUMBER" ]]; then
  error "Could not parse board number from: $BOARD_INPUT"
  exit 1
fi

info "Fetching board #$BOARD_NUMBER for user $BOARD_OWNER ..."
BOARD_JSON=$(gh project view "$BOARD_NUMBER" --owner "$BOARD_OWNER" --format json 2>/dev/null || true)

if [[ -z "$BOARD_JSON" ]]; then
  error "Could not access board #$BOARD_NUMBER for $BOARD_OWNER."
  echo "  Make sure the board exists and your token has 'project' scope."
  exit 1
fi

BOARD_TITLE=$(echo "$BOARD_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('title',''))")
PROJECT_ID=$(echo "$BOARD_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")
success "Found board: \"$BOARD_TITLE\" (ID: $PROJECT_ID)"

# Fetch Status field
STATUS_FIELD_DATA=$(gh project field-list "$BOARD_NUMBER" --owner "$BOARD_OWNER" --format json \
  --jq '.fields[] | select(.name == "Status")' 2>/dev/null || true)

if [[ -z "$STATUS_FIELD_DATA" ]]; then
  error "No 'Status' field found on board #$BOARD_NUMBER."
  echo "  Add a single-select 'Status' field to your board first."
  exit 1
fi

STATUS_FIELD_ID=$(echo "$STATUS_FIELD_DATA" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
PERSONAL_OPTIONS=$(gh project field-list "$BOARD_NUMBER" --owner "$BOARD_OWNER" --format json \
  --jq '[.fields[] | select(.name == "Status") | .options[]? | {name, id}]')
PERSONAL_STATUSES=$(echo "$PERSONAL_OPTIONS" | python3 -c "
import sys, json
opts = json.load(sys.stdin)
print(' · '.join(o['name'] for o in opts))
")

success "Status field ID: $STATUS_FIELD_ID"
info    "Status options: $PERSONAL_STATUSES"

# Detect "Done" option
DONE_STATUS=$(echo "$PERSONAL_OPTIONS" | python3 -c "
import sys, json, re
opts = json.load(sys.stdin)
# Find option whose bare name (no emoji) is 'Done'
for o in opts:
    bare = re.sub(r'^[\U00010000-\U0010ffff\s\-]+', '', o['name']).strip()
    if bare.lower() == 'done':
        print(o['name'])
        break
" 2>/dev/null || echo "Done")
info "Done status mapped to: \"$DONE_STATUS\""

# ── Step 3: Select repos ──────────────────────────────────────────────────────
header "Step 3: Select repos to sync"

echo "How would you like to specify repos?"
echo "  1) Enter a list manually"
echo "  2) Select interactively from your accessible repos (org/user)"
echo "  3) Scan ALL accessible repos (slow — may take several minutes)"
prompt "Choice [1/2/3]:"
read -r REPO_MODE

REPOS=()

case "$REPO_MODE" in
  1)
    echo ""
    info "Enter repos one per line as 'owner/repo'. Empty line to finish."
    while true; do
      prompt "  owner/repo:"
      read -r repo_input
      [[ -z "$repo_input" ]] && break
      # Validate format
      if [[ "$repo_input" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]; then
        REPOS+=("$repo_input")
        success "  Added: $repo_input"
      else
        warn "  Skipping invalid format: $repo_input (expected owner/repo)"
      fi
    done
    ;;

  2)
    echo ""
    info "Fetching repos you have access to (this may take a moment) ..."
    # List repos from orgs + personal
    ALL_REPOS=$(gh repo list --limit 200 --json nameWithOwner --jq '.[].nameWithOwner' 2>/dev/null || true)
    REPO_COUNT=$(echo "$ALL_REPOS" | grep -c . || true)
    info "Found $REPO_COUNT repos. Type repo numbers to select (space-separated), or 'all'."
    echo ""
    # Display numbered list
    i=1
    declare -A REPO_MAP
    while IFS= read -r r; do
      printf "  %3d) %s\n" "$i" "$r"
      REPO_MAP[$i]="$r"
      ((i++))
    done <<< "$ALL_REPOS"
    echo ""
    prompt "Select [e.g. 1 3 7 — or 'all']:"
    read -r SELECTION
    if [[ "$SELECTION" == "all" ]]; then
      while IFS= read -r r; do REPOS+=("$r"); done <<< "$ALL_REPOS"
    else
      for num in $SELECTION; do
        if [[ -n "${REPO_MAP[$num]:-}" ]]; then
          REPOS+=("${REPO_MAP[$num]}")
          success "  Selected: ${REPO_MAP[$num]}"
        else
          warn "  Invalid number: $num"
        fi
      done
    fi
    ;;

  3)
    echo ""
    warn "Full scan mode: querying ALL accessible repos. This can be very slow."
    prompt "Continue? [y/N]:"
    read -r ans; [[ "$ans" =~ ^[Yy]$ ]] || { info "Switching to manual mode."; exec "$0"; }
    info "Scanning all accessible repos ..."
    ALL_REPOS=$(gh repo list --limit 1000 --json nameWithOwner --jq '.[].nameWithOwner' 2>/dev/null || true)
    while IFS= read -r r; do REPOS+=("$r"); done <<< "$ALL_REPOS"
    success "Found ${#REPOS[@]} repos."
    ;;

  *)
    warn "Invalid choice. Defaulting to manual entry."
    exec "$0"
    ;;
esac

if [[ ${#REPOS[@]} -eq 0 ]]; then
  error "No repos selected. Exiting."
  exit 1
fi

echo ""
success "Selected ${#REPOS[@]} repos:"
for r in "${REPOS[@]}"; do echo "  - $r"; done

# ── Step 4: Inspect Status columns in origin repos ───────────────────────────
header "Step 4: Inspecting Status columns in origin repo projects"

# Normalize: strip leading emoji + whitespace for fuzzy comparison
normalize_status() {
  python3 -c "
import re, sys
s = '$1'
print(re.sub(r'^[\U00010000-\U0010ffff\s\-]+', '', s).strip())
" 2>/dev/null || echo "$1"
}

PERSONAL_BARE=$(echo "$PERSONAL_OPTIONS" | python3 -c "
import sys, json, re
opts = json.load(sys.stdin)
bare = [re.sub(r'^[\U00010000-\U0010ffff\s\-]+', '', o['name']).strip() for o in opts]
print(json.dumps(bare))
")

# Collect all origin project Status columns
declare -A ORIGIN_PROJECT_IDS    # project_title → project_id
declare -A ORIGIN_FIELD_IDS      # project_title → status_field_id
declare -A ORIGIN_STATUSES       # project_title → JSON array of {name,id}
declare -A REPO_TO_PROJECTS      # repo → space-separated project titles

echo ""
for repo in "${REPOS[@]}"; do
  owner="${repo%%/*}"; name="${repo##*/}"
  projects=$(gh api graphql -f query="
    query {
      repository(owner: \"$owner\", name: \"$name\") {
        projectsV2(first: 10) {
          nodes {
            id title
            fields(first: 20) {
              nodes {
                ... on ProjectV2SingleSelectField {
                  id name options { id name }
                }
              }
            }
          }
        }
      }
    }
  " --jq '.data.repository.projectsV2.nodes[] |
      {id, title, statusField: (.fields.nodes[] | select(.name == "Status") | {id, options})}
  ' 2>/dev/null || true)

  if [[ -z "$projects" ]]; then
    info "  $repo — no projects found (or no access)"
    continue
  fi

  repo_projects=()
  while IFS= read -r proj; do
    [[ -z "$proj" ]] && continue
    p_title=$(echo "$proj" | python3 -c "import sys,json; print(json.loads(sys.stdin.read())['title'])")
    p_id=$(echo "$proj"    | python3 -c "import sys,json; print(json.loads(sys.stdin.read())['id'])")
    p_opts=$(echo "$proj"  | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(json.dumps(d.get('statusField',{}).get('options',[])))")
    p_fid=$(echo "$proj"   | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('statusField',{}).get('id',''))")

    ORIGIN_PROJECT_IDS["$p_title"]="$p_id"
    ORIGIN_FIELD_IDS["$p_title"]="$p_fid"
    ORIGIN_STATUSES["$p_title"]="$p_opts"
    repo_projects+=("$p_title")

    # Compare with personal board
    mismatch=$(python3 -c "
import sys, json, re
def bare(s): return re.sub(r'^[\U00010000-\U0010ffff\s\-]+', '', s).strip()
personal = set(bare(o['name']) for o in $PERSONAL_OPTIONS)
origin   = [o['name'] for o in $p_opts]
missing_in_origin  = [n for n in [o['name'] for o in $(echo $PERSONAL_OPTIONS)] if bare(n) not in {bare(o) for o in origin}]
missing_in_personal = [n for n in origin if bare(n) not in personal]
print(json.dumps({'missing_in_origin': missing_in_origin, 'missing_in_personal': missing_in_personal}))
" 2>/dev/null || echo '{"missing_in_origin":[],"missing_in_personal":[]}')

    miss_orig=$(echo "$mismatch" | python3 -c "import sys,json; d=json.load(sys.stdin); print(', '.join(d['missing_in_origin']))")
    miss_pers=$(echo "$mismatch" | python3 -c "import sys,json; d=json.load(sys.stdin); print(', '.join(d['missing_in_personal']))")

    if [[ -z "$miss_orig" && -z "$miss_pers" ]]; then
      success "  $repo → \"$p_title\": ✓ fully aligned"
    else
      warn "  $repo → \"$p_title\":"
      [[ -n "$miss_orig" ]] && warn "    Missing in origin project: $miss_orig"
      [[ -n "$miss_pers" ]] && warn "    Missing in personal board: $miss_pers (will be mapped)"
    fi
  done < <(echo "$projects")
  REPO_TO_PROJECTS["$repo"]="${repo_projects[*]:-}"
done

# ── Step 5: Fix inconsistencies ───────────────────────────────────────────────
header "Step 5: Fixing Status column inconsistencies"

# Collect all projects that have missing options vs personal board
PROJECTS_TO_FIX=()
for p_title in "${!ORIGIN_STATUSES[@]}"; do
  p_opts="${ORIGIN_STATUSES[$p_title]}"
  miss_orig=$(python3 -c "
import sys, json, re
def bare(s): return re.sub(r'^[\U00010000-\U0010ffff\s\-]+', '', s).strip()
personal = $(echo "$PERSONAL_OPTIONS")
origin   = $p_opts
missing  = [o['name'] for o in personal if bare(o['name']) not in {bare(x['name']) for x in origin}]
print(json.dumps(missing))
" 2>/dev/null || echo "[]")
  count=$(echo "$miss_orig" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
  if [[ "$count" -gt 0 ]]; then
    PROJECTS_TO_FIX+=("$p_title")
  fi
done

if [[ ${#PROJECTS_TO_FIX[@]} -eq 0 ]]; then
  success "No fixes needed — all origin projects are aligned with your personal board."
else
  echo ""
  warn "The following projects are missing Status options:"
  for t in "${PROJECTS_TO_FIX[@]}"; do echo "  - $t"; done
  echo ""
  prompt "Attempt to fix by adding missing options to origin projects? [Y/n]:"
  read -r fix_ans

  if [[ ! "$fix_ans" =~ ^[Nn]$ ]]; then
    for p_title in "${PROJECTS_TO_FIX[@]}"; do
      p_id="${ORIGIN_PROJECT_IDS[$p_title]}"
      p_fid="${ORIGIN_FIELD_IDS[$p_title]}"
      p_opts="${ORIGIN_STATUSES[$p_title]}"

      info "Fixing \"$p_title\" ..."

      # Build full merged options list: existing (with IDs) + new ones from personal board
      merged=$(python3 -c "
import sys, json, re
def bare(s): return re.sub(r'^[\U00010000-\U0010ffff\s\-]+', '', s).strip()

personal = $(echo "$PERSONAL_OPTIONS")
existing = $p_opts

existing_bare = {bare(o['name']): o for o in existing}

result = []
for p in personal:
    b = bare(p['name'])
    if b in existing_bare:
        # Keep existing id, adopt personal board name (adds emoji if missing)
        result.append({'id': existing_bare[b]['id'], 'name': p['name']})
    else:
        # New option — no id
        result.append({'name': p['name']})

print(json.dumps(result))
")

      # Build GraphQL input
      options_gql=$(echo "$merged" | python3 -c "
import sys, json
opts = json.load(sys.stdin)
parts = []
for o in opts:
    if 'id' in o:
        parts.append(f'{{id: \"{o[\"id\"]}\", name: \"{o[\"name\"]}\", color: GRAY, description: \"\"}}')
    else:
        parts.append(f'{{name: \"{o[\"name\"]}\", color: GRAY, description: \"\"}}')
print('\n'.join(parts))
")

      result=$(gh api graphql -f query="
        mutation {
          updateProjectV2Field(input: {
            fieldId: \"$p_fid\"
            singleSelectOptions: [
              $options_gql
            ]
          }) {
            projectV2Field {
              ... on ProjectV2SingleSelectField { name options { id name } }
            }
          }
        }
      " 2>/dev/null || true)

      if echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); d['data']['updateProjectV2Field']['projectV2Field']" &>/dev/null; then
        success "  Fixed \"$p_title\""
        # Update cached options
        new_opts=$(echo "$result" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(json.dumps(d['data']['updateProjectV2Field']['projectV2Field']['options']))
")
        ORIGIN_STATUSES["$p_title"]="$new_opts"
      else
        warn "  Could not fix \"$p_title\" (no write access?) — will add to status_map.json"
      fi
    done
  fi
fi

# ── Step 6: Generate status_map.json for unresolved mismatches ────────────────
header "Step 6: Generating status_map.json for remaining mismatches"

STATUS_MAP="{}"
has_map=false

for p_title in "${!ORIGIN_STATUSES[@]}"; do
  p_opts="${ORIGIN_STATUSES[$p_title]}"
  p_id="${ORIGIN_PROJECT_IDS[$p_title]}"

  mapping=$(python3 -c "
import sys, json, re
def bare(s): return re.sub(r'^[\U00010000-\U0010ffff\s\-]+', '', s).strip()

personal = $(echo "$PERSONAL_OPTIONS")
origin   = $p_opts

personal_by_bare = {bare(o['name']): o['name'] for o in personal}
origin_by_bare   = {bare(o['name']): o['name'] for o in origin}

# Map: origin_status_name → personal_status_name  (where names differ)
m = {}
for ob, on in origin_by_bare.items():
    if ob in personal_by_bare and personal_by_bare[ob] != on:
        m[on] = personal_by_bare[ob]

print(json.dumps(m))
" 2>/dev/null || echo "{}")

  count=$(echo "$mapping" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
  if [[ "$count" -gt 0 ]]; then
    has_map=true
    info "  \"$p_title\" needs $count name mapping(s)"
    STATUS_MAP=$(python3 -c "
import sys, json
base = $STATUS_MAP
new  = {'$p_id': $mapping}
base.update(new)
print(json.dumps(base, indent=2))
")
  fi
done

if $has_map; then
  echo "$STATUS_MAP" > "$STATUS_MAP_FILE"
  success "Written: status_map.json"
  info "  sync.sh will use this to translate status names between projects."
else
  success "No name mappings needed — status_map.json not required."
  [[ -f "$STATUS_MAP_FILE" ]] && rm "$STATUS_MAP_FILE"
fi

# ── Step 7: Write config.sh ───────────────────────────────────────────────────
header "Step 7: Writing config.sh"

REPOS_SH=""
for r in "${REPOS[@]}"; do
  REPOS_SH+="  \"$r\"\n"
done

cat > "$CONFIG_FILE" <<CONFIGEOF
#!/usr/bin/env bash
# Auto-generated by setup.sh on $(date '+%Y-%m-%d %H:%M:%S')
# Do not commit this file — it is gitignored.

BOARD_OWNER="$BOARD_OWNER"
BOARD_NUMBER="$BOARD_NUMBER"
ASSIGNEE="$ASSIGNEE"
STATUS_FIELD_ID="$STATUS_FIELD_ID"
DONE_STATUS="$DONE_STATUS"
STATE_FILE="\${HOME}/.sync-gh-board/state.json"

REPOS=(
$(printf '%s' "$REPOS_SH")
)
CONFIGEOF

success "Written: config.sh"
chmod 600 "$CONFIG_FILE"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}Setup complete!${RESET}"
echo ""
echo "Next steps:"
echo "  • Run a one-off sync:        ./sync.sh"
echo "  • Schedule hourly sync (cron):"
echo "      (crontab -l 2>/dev/null; echo \"0 * * * * $(pwd)/sync.sh\") | crontab -"
echo "  • View logs:                 tail -f ~/.sync-gh-board/logs/\$(date '+%Y-%m-%d').log"
echo ""
