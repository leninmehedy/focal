# Contributing to Focal

## Commit message convention

Focal uses [Conventional Commits](https://www.conventionalcommits.org/). Every
commit message on `main` is parsed by semantic-release to determine the next
version and generate the changelog automatically.

| Prefix | Example | Version bump |
|---|---|---|
| `feat:` | `feat: add dry-run mode` | minor (1.x.0) |
| `fix:` | `fix: handle empty status field` | patch (1.0.x) |
| `chore:` / `docs:` / `refactor:` / `style:` / `test:` | — | no release |
| `feat!:` or `BREAKING CHANGE:` in footer | — | major (x.0.0) |

## Workflow

1. Fork the repo and create a branch from `main`.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install ruff
   ```
3. Make your changes. Run linting locally before pushing:
   ```bash
   # Python lint + format check
   ruff check focal.py focal/
   ruff format --check focal.py focal/

   # Shell wrappers
   shellcheck sync.sh setup.sh
   ```
4. Open a pull request against `main`. CI will run all checks automatically.
5. Once merged, semantic-release will tag and publish a new release if the
   commit type warrants one.

## Local development tips

- Run a sync: `python3 focal.py sync` — logs go to `~/.focal/logs/`
- Run setup: `python3 focal.py setup`
- Reset state: `rm ~/.focal/state.json` — next sync re-inherits all statuses
- `config.json` and `status_map.json` are gitignored — never commit them
- All GitHub API calls are in `focal/gh.py` — good starting point for new features
