# Pre-commit Hook Notes

A learning-oriented walkthrough of the `pre-commit` framework and how it's used in `kyomei_api`. Written after the "Add `pytest` to a pre-commit hook" item in `fastapi-backend-setup-checklist.md`'s Section 5 (Testing) was implemented and verified.

## Fundamentals

The problem this solves: CI (see [[cicd-notes]]) catches a broken test or lint violation, but only *after* a push — by then a PR is already open, or a teammate is already reviewing code that fails checks it hasn't even run yet. A **pre-commit hook** is a script Git runs locally, before a commit is finalized, that can block the commit if it fails. It moves the same feedback CI gives from "minutes after you pushed" to "seconds before you committed."

`pre-commit` (the framework, distinct from the generic Git hook it configures) is a thin manager on top of that: instead of hand-writing a `.git/hooks/pre-commit` shell script, you declare hooks in a checked-in `.pre-commit-config.yaml`, and the framework installs/wires them into `.git/hooks/pre-commit` for you. That config is versioned with the repo, so every clone gets the same hooks instead of each developer maintaining their own local script.

## Terminology

- **Hook (Git concept)** — an executable Git runs at a specific point in its workflow (`pre-commit`, `pre-push`, `commit-msg`, etc.). Git ships `.sample` versions of all of these in `.git/hooks/`; none are active until a real (non-`.sample`) file exists at that path. This repo had none before this change.
- **Hook (pre-commit-framework concept)** — one entry under a repo's `hooks:` list in `.pre-commit-config.yaml`; a single check (e.g. "run ruff check"). Confusingly the same word as the Git concept above but one level more granular — several framework hooks can share one Git hook stage.
- **`repo: local`** — tells `pre-commit` this hook's command is defined inline in this repo's own config, not fetched from an external hooks repo. The alternative is pointing at a hosted repo (e.g. `https://github.com/astral-sh/ruff-pre-commit`) that ships its own pinned tool version.
- **`language: system`** — tells `pre-commit` to just run `entry:` as a shell command using whatever's already on `PATH`/available via `uv run`, instead of creating and managing its own isolated environment for the hook (which is what most `language: python`/`language: node` hosted hooks do).
- **Stage** — which Git hook a framework hook is wired into. The default (used here, no explicit `stages:` key) is `pre-commit` itself; `pre-push` is the common alternative for slower checks.
- **`pass_filenames`** — whether `pre-commit` appends the list of changed/staged files to the hook's command. `false` here means every hook always checks the whole project, matching how `just lint`/`just test` already invoke `ruff`/`pytest` with no path arguments.

## How it's used in this project

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: ruff-check
        name: ruff check
        entry: uv run ruff check
        language: system
        types: [python]
        pass_filenames: false
      - id: ruff-format-check
        name: ruff format --check
        entry: uv run ruff format --check
        language: system
        types: [python]
        pass_filenames: false
      - id: pytest
        name: pytest
        entry: uv run pytest
        language: system
        pass_filenames: false
        always_run: true
```

- **`local` + `language: system` for all three hooks, not the hosted `ruff-pre-commit` mirror** — `ruff-pre-commit` pins its own ruff version independently of `uv.lock`. Using `uv run ruff check`/`uv run ruff format --check` instead means there's exactly one place ruff's version is pinned (`pyproject.toml`'s dev group + `uv.lock`), and the hook, `just lint`/`just format`, and CI's `uv run ruff check` step are always running the literal same installed binary — no risk of the hook passing on a different ruff version than CI enforces.
- **`pytest` runs at the `pre-commit` stage, not `pre-push`** — the checklist item explicitly asked for a pre-commit hook, so the full suite runs on every commit rather than being deferred to push time. The tradeoff is slower commits as the test suite grows; if that becomes painful, moving the `pytest` hook to `stages: [pre-push]` (keeping `ruff-check`/`ruff-format-check` fast and on every commit) is the natural next step — not done here because it wasn't asked for.
- **`ruff format --check`, not `ruff format`** — the hook should *fail* on unformatted code, not silently rewrite files out from under a commit already staged in the index. `just format` (which does rewrite files) stays the tool you run manually to fix what the hook flags.
- **`always_run: true` on `pytest`** — without it, `pre-commit` would skip a hook whose `types:`/file-pattern doesn't match any staged file; `pytest` has no `types:` filter (it isn't scoped to Python files the way ruff is — a test can fail because of a config or fixture change too), so `always_run` guarantees it never gets silently skipped.

## Setup and usage

```
uv sync              # installs `pre-commit` — it's in pyproject.toml's dev dependency group, so a plain `uv sync` (no --group flag) picks it up, same as pytest/ruff already did
just hooks-install    # uv run pre-commit install — one-time per clone, wires .git/hooks/pre-commit
just hooks-run        # uv run pre-commit run --all-files — runs every hook against the whole repo without committing anything; useful for a first-time check or after editing the config
```

Once installed, `git commit` runs all three hooks automatically and aborts the commit if any fail, printing the failing tool's own output. `git commit --no-verify` skips every hook for that one commit — an escape hatch for a genuinely broken local environment, not a routine habit, since it just relocates the same failure to whenever CI runs `uv run ruff check`/`uv run pytest` instead.

## Further learning

- [pre-commit — official docs](https://pre-commit.com/) — the framework's own reference for `.pre-commit-config.yaml` syntax, hook stages, and the `local`/`language: system` combination used here.
- [pre-commit — Creating new hooks](https://pre-commit.com/#new-hooks) — background on what `language:`, `entry:`, `types:`, and `pass_filenames` actually control.
- [[cicd-notes]] — the CI workflow this hook set mirrors (`ruff check` + `pytest`), and why `uv run <tool>` (rather than a bare `<tool>` on `PATH`) is this project's standing convention across CI, `justfile`, and now pre-commit hooks.
