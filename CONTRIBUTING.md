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
2. Make your changes. Run linting locally before pushing:
   ```bash
   shellcheck sync.sh setup.sh
   shfmt --diff --indent 2 sync.sh setup.sh
   ```
3. Open a pull request against `main`. CI will run shellcheck and shfmt automatically.
4. Once merged, semantic-release will tag and publish a new release if the
   commit type warrants one.

## Local development tips

- Test changes by running `./sync.sh` directly — it logs to `~/.focal/logs/`.
- Use `bash -x ./sync.sh 2>&1 | head -100` to trace execution.
- Reset state with `rm ~/.focal/state.json` to re-run a clean sync.
- `config.sh` and `status_map.json` are gitignored — never commit them.
