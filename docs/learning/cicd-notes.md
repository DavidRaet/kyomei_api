# CI/CD Notes

A learning-oriented walkthrough of CI/CD and how it's used in `kyomei_api`. Written after Section 7 of `fastapi-backend-setup-checklist.md` (CI/CD) was implemented and verified.

## Fundamentals

CI/CD automates the two steps between "I changed some code" and "that change is safely running somewhere": verifying it (**Continuous Integration**) and shipping it (**Continuous Deployment/Delivery**). The problem it solves is trusting change at speed — without it, "does this still work?" and "is this safe to release?" are answered by a human remembering to run the right commands, which doesn't scale and doesn't happen consistently.

- **Continuous Integration (CI)** — every change (typically every PR) is automatically built, linted, and tested in a clean, disposable environment, so regressions are caught before merge rather than discovered later. This project's CI does this: `ruff check` + `pytest` + a Docker build, on every PR.
- **Continuous Delivery** — CI's output (a build artifact/image) is automatically produced in a release-ready state, but a human still decides when/whether to actually deploy it.
- **Continuous Deployment** — a step further: every change that passes CI is deployed automatically, no human gate. This project doesn't do this yet — the (Later) auto-deploy step in checklist Section 7 is deferred until Section 8 (Deployment, Railway) is decided.

## Terminology

- **Workflow** — a YAML file (`.github/workflows/*.yml`) describing what to automate and when. A repo can have several, each independent.
- **Trigger (`on:`)** — the event(s) that start a workflow run: `pull_request`, `push`, `workflow_dispatch` (manual button), `schedule` (cron), etc. This project triggers on `pull_request` (any branch) and `push` to `main`.
- **Job** — an independent unit of work within a workflow. Jobs run in parallel by default, each on its own fresh virtual machine (`runs-on:`), unless one explicitly depends on another (`needs:`). This project has two jobs — `lint-and-test` and `docker-build` — that run concurrently rather than one blocking the other.
- **Step** — an ordered instruction inside a job: either `uses:` (run a prebuilt, reusable **Action**) or `run:` (execute a shell command). Steps in a job share a filesystem and run sequentially.
- **Action** — a packaged, reusable unit of automation (e.g. `actions/checkout`, `astral-sh/setup-uv`), referenced by `owner/repo@version`. Pinning a version (`@v4`, `@v5`) avoids a third-party update silently changing your pipeline's behavior.
- **Runner** — the (usually ephemeral, freshly-provisioned) machine that executes a job. `ubuntu-latest` here means every run starts from a clean Ubuntu VM with nothing cached from a previous run except what an Action explicitly caches.
- **Matrix build** — running the same job across multiple variable combinations (e.g. several Python versions/OSes) in parallel. Not used in this project — a single job version (matching `.python-version`) is enough for a service with one deploy target.
- **Status check** — a job's pass/fail result reported back to the triggering commit/PR; GitHub can be configured to block merging until required checks are green (branch protection — not yet configured here).
- **Caching** — reusing files (dependency downloads, build layers) across runs instead of refetching them every time, to speed up otherwise-identical work. `astral-sh/setup-uv`'s `enable-cache: true` caches `uv`'s package downloads between workflow runs.

## How it's used in this project

The workflow at `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync
      - run: uv run ruff check
      - run: uv run pytest

  docker-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t kyomei-api:ci .
```

- **Two independent jobs, not one** — `lint-and-test` and `docker-build` run in parallel on separate runners. A slow Docker build never delays lint/test feedback on a PR, and a lint failure doesn't block the Docker job from also reporting its own result. The tradeoff: total runner-minutes used is higher than one sequential job, which is a non-issue at this project's size.
- **`astral-sh/setup-uv@v5`** — installs `uv` on the runner and (per checklist/Dockerfile precedent) picks up this repo's `.python-version` (`3.14`) automatically, so CI's Python version matches local dev and the Docker image without a separate `actions/setup-python` step or hardcoded version string.
- **`uv sync` with no flags** — installs the project's main dependencies *and* the default `dev` dependency group, which is why `pytest` (added to `pyproject.toml`'s `dev` group specifically for this CI step) gets installed without an extra `--group` flag.
- **`uv run ruff check` / `uv run pytest`** — run through `uv run` rather than assuming `ruff`/`pytest` are on `PATH` directly; this matches how the project's `justfile` (`just lint`, `just test`) invokes them, so CI and local dev run the exact same commands.
- **A real test to check, not zero** — before this change, `tests/` had no test files and `pytest` wasn't even a dependency; a bare `pytest` step would have either errored (missing package) or exited with code 5 ("no tests collected"), making the CI check meaningless. `tests/test_health.py` (a `TestClient` hit against the existing `GET /health` route) was added specifically so `pytest` has one real, passing thing to verify.
- **`docker-build` has no push step** — it runs `docker build` only, to catch a broken `Dockerfile`/build context early (e.g. a `COPY` path typo, a dependency that fails to resolve in the container's base image). It intentionally does not push to a registry — that belongs to the deferred Section 8 deploy work, once Railway is wired up.
- **No `workflow_dispatch` or `schedule` trigger** — this pipeline only needs to answer "is this PR/this push to `main` safe," so `pull_request` + `push: branches: [main]` is the full trigger set; nothing here needs a manual button or a nightly run yet.

## Important commands

Commands relevant to working with this project's GitHub Actions setup:

```
gh workflow list                       # list workflows in the repo
gh workflow view ci.yml                # show a workflow's details
gh run list --workflow=ci.yml          # list recent runs of this workflow
gh run view <run-id> --log             # view full logs for a specific run
gh run watch <run-id>                  # stream a run's status live
gh pr checks <pr-number>               # show CI status for a specific PR
```

Commands used to verify the workflow's steps would pass *before* pushing (so CI's first real run isn't the first time these commands are tried):

```
uv sync                                # confirms pytest resolves/installs like CI's `uv sync` step would
uv run ruff check                      # same lint check CI runs
uv run pytest                          # same test command CI runs
docker build -t kyomei-api:ci .        # same build CI's docker-build job runs
```

## Further learning

- [GitHub Actions — Understanding GitHub Actions](https://docs.github.com/en/actions/learn-github-actions/understanding-github-actions) — official fundamentals walkthrough (workflows, jobs, steps, runners).
- [GitHub Actions — Workflow syntax reference](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions) — full YAML syntax reference for `on:`, `jobs:`, `steps:`, etc.
- [`astral-sh/setup-uv`](https://github.com/astral-sh/setup-uv) — the exact Action this project uses to install `uv` and manage caching in CI.
- [GitHub Actions — Branch protection / required status checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) — how to actually make a green `CI` check required before merge (not yet configured in this repo).
- [Railway — Deploying with Docker](https://docs.railway.com/guides/dockerfiles) — relevant once checklist Section 8 (Deployment) picks up the deferred auto-deploy step from Section 7.
