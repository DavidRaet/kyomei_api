# Docker Notes

A learning-oriented walkthrough of Docker and how it's used in `kyomei_api`. Written after Section 6 of `fastapi-backend-setup-checklist.md` (Containerization) was implemented and verified.

## Fundamentals

Docker packages an application together with everything it needs to run — interpreter, libraries, system packages, config — into a single unit that behaves identically on any machine that can run Docker. That's the problem it solves: "works on my machine" stops being a real category of bug because the machine (in the relevant sense) travels with the app.

Three core concepts:

- **Image** — a read-only, layered filesystem snapshot plus metadata (what command to run, what port to expose, etc.). Built once from a `Dockerfile`, then reused. Think of it as a class.
- **Container** — a running (or stopped) instance of an image, with its own writable layer on top and its own process namespace/network. Think of it as an object instantiated from that class. You can run many containers from one image.
- **Registry** — a server that stores and distributes images by name+tag (e.g. Docker Hub, GitHub Container Registry — `ghcr.io`, which this project pulls its base image from). `docker pull`/`docker push` move images to/from a registry; `docker build` produces one locally.

## Terminology

- **Layer** — each instruction in a `Dockerfile` (`RUN`, `COPY`, etc.) produces one filesystem layer, cached and stacked on top of the previous one. Unchanged layers are reused on rebuild, which is why *instruction order* matters (put things that change least often first).
- **Base image** — the `FROM` image everything else builds on top of.
- **Build context** — the set of files sent to the Docker daemon when you run `docker build .` (everything in the directory, minus what `.dockerignore` excludes). A bloated context slows every build and can leak files (`.env`, `.git`) into the image if not excluded.
- **`Dockerfile` instructions** used in this project:
  - `FROM` — pick the base image.
  - `WORKDIR` — set the working directory for subsequent instructions (and the container's default CWD).
  - `COPY` — copy files from the build context into the image.
  - `RUN` — execute a command at build time, baking its result into a new layer.
  - `ENV` — set an environment variable, available at both build and run time.
  - `EXPOSE` — documents which port the container listens on (doesn't actually publish it — that's `docker run -p`).
  - `CMD` — the default command a container runs when started (overridable at `docker run` time; not baked in as immutably as `RUN`).
- **`.dockerignore`** — same idea as `.gitignore`, but for the build context: keeps `.venv`, `.git`, secrets, and dev-only files out of the image and off the wire to the daemon.
- **Tag** — a label on an image (e.g. `kyomei-api:latest`), usually `name:version`. Untagged builds default to `latest`.

## How it's used in this project

The `Dockerfile` at the repo root:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim
WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY app ./app
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

- **Base image** — `ghcr.io/astral-sh/uv:python3.14-bookworm-slim` is `uv`'s own published image: a slim Debian Bookworm image with Python 3.14 and the `uv` binary already installed. This gets the "small base image" checklist goal without a manual `pip install uv` step, and keeps the container's Python version in sync with `.python-version` (also 3.14).
- **No multi-stage build** — this project's dependencies (`fastapi`, `httpx`, `pydantic-settings`, `uvicorn[standard]`) all ship prebuilt wheels, so nothing needs a compiler toolchain that would otherwise bloat the final image. A single stage is enough.
- **Two-layer `uv sync`** — dependencies are installed *before* the app code is copied in (`COPY pyproject.toml uv.lock ./` → `uv sync --no-install-project`), then the app code is copied and synced again. Because Docker caches each layer, editing application code doesn't invalidate (and re-run) the dependency-install layer — only `RUN uv sync --frozen --no-dev` (fast, no network) and the final image export re-run. Editing `pyproject.toml`/`uv.lock` is what invalidates the slow layer.
- **`UV_LINK_MODE=copy`** — avoids `uv`'s default hardlink behavior, which can misbehave across Docker's layer filesystem boundaries; `UV_COMPILE_BYTECODE=1` precompiles `.pyc` files at build time instead of on first request.
- **`ENV PATH="/app/.venv/bin:$PATH"`** — puts the project's virtualenv on `PATH` so the container's `CMD` can call `uvicorn` directly rather than needing `uv run uvicorn ...` (marginally faster startup, one less layer of indirection).
- **`${PORT:-8000}` in `CMD`** — Railway (this project's target host, per checklist Section 8) assigns its own `PORT` env var at runtime; the shell expansion picks that up if present and falls back to `8000` for a plain local `docker run`. This only works because `CMD` uses the shell form (`sh -c "..."`) — the exec-array form (`CMD ["uvicorn", ...]`) doesn't expand env vars.
- **`.dockerignore`** — excludes `.venv`, `.git`, `.claude`, caches, `tests/`, `docs/`, markdown files, and `.env*` (except the checked-in `.env.example`) from the build context, so local dev cruft and secrets never reach the image.

## Important commands

Commands actually used to build and verify this project's image:

```
docker build -t kyomei-api .              # build an image from the Dockerfile, tagged "kyomei-api"
docker run --rm -p 8000:8000 kyomei-api   # run a container, map host:container port, auto-remove on exit
docker run -d --rm -p 8000:8000 kyomei-api  # same, but detached (returns immediately, container runs in background)
docker ps                                 # list running containers
docker logs <container>                  # view a container's stdout/stderr (e.g. uvicorn's startup logs)
docker exec -it <container> sh           # open a shell inside a running container, for poking around
docker stop <container>                  # stop a running container
docker image ls                          # list local images
docker system prune                      # reclaim disk space from stopped containers / dangling layers
```

Verification performed for this project:

```
docker build -t kyomei-api .
docker run -d --rm --name kyomei-api-test -p 8124:8000 kyomei-api
curl http://localhost:8124/health         # -> {"status":"ok"}, HTTP 200
docker run -d --rm -p 9001:9001 -e PORT=9001 kyomei-api
curl http://localhost:9001/health         # confirms Railway-style PORT injection works too
```

## Further learning

- [Docker docs — Get started](https://docs.docker.com/get-started/) — official fundamentals walkthrough (images, containers, `Dockerfile` reference).
- [Docker `Dockerfile` reference](https://docs.docker.com/reference/dockerfile/) — full instruction-by-instruction reference.
- [`uv` — Using uv in Docker](https://docs.astral.sh/uv/guides/integration/docker/) — the exact base-image and layer-caching pattern this project's Dockerfile follows.
- [Railway — Deploying with Docker](https://docs.railway.com/guides/dockerfiles) — how Railway builds/runs a `Dockerfile`-based service, relevant for checklist Section 8.
