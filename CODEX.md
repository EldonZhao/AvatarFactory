# CODEX.md

This file describes the preferred workflow when developing AvatarFactory with Codex.

## 0) Local Runtime Principle

- Local run must use Docker containers.
- Do not run backend/frontend services directly on host machine.

## 1) Repository Map

- `avatarfactory/`: Python backend (CLI, agents, service, scheduler, connectors)
- `web-admin/`: Astro admin UI (default port `4323`)
- `web-journal/`: Astro public journal UI (default port `4328`)
- `tests/`: Python tests
- `scripts/`: setup and deployment scripts
- `docs/`: architecture and deployment docs

## 2) Codex-First Commands (Docker)

Run from repository root:

```bash
make setup
make up
make test
make lint
```

`make setup` builds development images from `docker-compose.dev.yml`.

## 3) Container Endpoints

- API: `http://127.0.0.1:8000`
- Admin UI: `http://127.0.0.1:4323`
- Journal UI: `http://127.0.0.1:4328`
- Backend env file: `.env` (mounted into `api` container)

## 4) Design & Frontend Iteration Flow

1. Start all containers: `make up`
2. Iterate in `web-admin/src/components` and `web-admin/src/pages`
3. Build-check with `make web-build`
4. Stop containers with `make down`

For public content pages, iterate in `web-journal/` while `make up` is running.

## 5) Quality Gate

Before opening a PR:

```bash
make check
```

This runs formatting check, lint, and tests in one pass.
