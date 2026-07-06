# Agent Platform OS

Agent Platform OS is the production root control plane for a five-service AI operations fabric.
It provides the workspace contract, service catalog, environment validation, Docker orchestration,
bootstrap automation, a Hydra worker runtime, an operator CLI, and health verification needed to
run the platform as one coordinated system.

The root repository does not duplicate service business logic. Each service remains an independent
Python package under `services/*`, while this repository owns the runtime contract that lets them
operate together.

## Completion Boundary

This repository is complete as the root Agent Platform OS control plane. It includes the typed
root package, environment contract, service catalog, bootstrap automation, container launcher,
Docker Compose fabric, Hydra worker process, health verification suite, CLI connector, CI workflow,
tests, and operations documentation.

The five runtime services are intentionally maintained as separate repositories. They are cloned
into `services/*` for local or deployment assembly by running:

```bash
uv run python scripts/bootstrap_services.py
```

## Coordinated Services

| Service | Repository | Runtime Role |
| --- | --- | --- |
| `async_mcp_gateway` | [`fernandogarzaaa/async-mcp-gateway`](https://github.com/fernandogarzaaa/async-mcp-gateway) | Zero-trust MCP/LLM ingress, rate limiting, provider failover, and streaming safety. |
| `hydra_engine` | [`fernandogarzaaa/hydra-engine`](https://github.com/fernandogarzaaa/hydra-engine) | Durable PostgreSQL-backed execution with crash replay for agent steps. |
| `synapse_mesh` | [`fernandogarzaaa/SynapseMesh`](https://github.com/fernandogarzaaa/SynapseMesh) | Semantic model routing and SpatialFlux VLA command intake. |
| `swarm_bus` | [`fernandogarzaaa/swarm-bus`](https://github.com/fernandogarzaaa/swarm-bus) | Redis Streams event bus with atomic task locking and loop isolation. |
| `spatial_flux` | [`fernandogarzaaa/Spatial-Flux`](https://github.com/fernandogarzaaa/Spatial-Flux) | Edge video ingestion and structural-drift-triggered cloud VLA routing. |

## Architecture

```text
user ingress
  -> async_mcp_gateway
  -> hydra_engine API + hydra_engine_worker
  -> synapse_mesh
  -> swarm_bus
  -> spatial_flux
  -> PostgreSQL and Redis durability backbones
```

## Repository Layout

```text
agent-platform-os/
|-- agent_platform_os/          # typed root orchestration package
|-- scripts/
|   |-- bootstrap_services.py   # clone or fast-forward service repos
|   |-- check_health.py         # async platform health verifier
|   |-- install.py              # one-command root and service installer
|   |-- platform_cli.py         # human and Codex operator commands
|   `-- run_service.py          # container service launcher
|-- tests/                      # root package and health target tests
|-- .github/workflows/ci.yml    # CI validation gate
|-- .env.example                # complete environment manifest
|-- docker-compose.yml          # production-oriented local fabric
|-- Dockerfile                  # hardened root service launcher image
`-- pyproject.toml              # uv workspace and lint/type config
```

Service checkouts are intentionally ignored by Git and should live at:

```text
services/async_mcp_gateway
services/hydra_engine
services/synapse_mesh
services/swarm_bus
services/spatial_flux
```

## One-Line Install

For a fresh machine with Python and Git installed, run one of these commands from the directory
where you want the platform folder created.

PowerShell:

```powershell
irm https://raw.githubusercontent.com/fernandogarzaaa/agent-platform-os/main/scripts/install.py | python -
```

macOS or Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/fernandogarzaaa/agent-platform-os/main/scripts/install.py | python3 -
```

The installer clones or updates the root repository at `agent-platform-os`, creates `.env` from
`.env.example` when it does not already exist, clones all five required service repositories under
`services/*`, and runs `uv sync --extra dev` when `uv` is available.

To update an existing installation:

```bash
python scripts/install.py --update
```

## Start And Use

Install dependencies:

```bash
uv sync --extra dev
```

Create local configuration:

```bash
cp .env.example .env
```

Clone all five services:

```bash
uv run python scripts/bootstrap_services.py
```

Start the platform:

```bash
docker compose up --build -d
```

Run health verification:

```bash
uv run python scripts/check_health.py
```

Run the operator CLI:

```bash
uv run python scripts/platform_cli.py health
uv run python scripts/platform_cli.py workflow-demo
uv run python scripts/platform_cli.py bus-demo
uv run python scripts/platform_cli.py spatial-demo
```

## Runtime Behavior

The Compose fabric starts PostgreSQL and Redis first, waits for their health checks, and then
starts service containers. Each service container mounts its corresponding `services/*` checkout,
validates that `pyproject.toml` and `app/main.py` are present, synchronizes dependencies with
`uv`, and launches the FastAPI app with `uvicorn app.main:app`.

The fabric also starts `hydra_engine_worker`, which consumes queued workflows and advances them
from `PENDING` to `COMPLETED` or `FAILED`. If a service checkout is absent or malformed, the
container exits with a clear error instead of idling.

## AI Model Setup

The platform can run deterministic local workflow steps without model credentials. To make Hydra
prompt steps call the gateway, set `HYDRA_USE_GATEWAY_MODEL=true` in `.env` and configure one
provider:

```bash
OPENAI__API_KEY=replace-with-your-openai-api-key
OPENAI__BASE_URL=https://api.openai.com
OPENAI__DEFAULT_MODEL=gpt-4o-mini
```

For a local OpenAI-compatible provider such as Axiom or Ollama, point the local provider at the
host service:

```bash
LOCAL__BASE_URL=http://host.docker.internal:3000
LOCAL__DEFAULT_MODEL=local-fallback
```

ChatGPT/Codex subscriptions do not act as backend API credentials. Codex can operate this platform
through `scripts/platform_cli.py`, while the platform itself needs an API key or local
OpenAI-compatible model endpoint for real model calls.

## Port Map

| Component | Host Port | Internal DNS |
| --- | ---: | --- |
| PostgreSQL | `5432` | `postgres_db` |
| Redis | `6379` | `redis_broker` |
| `async_mcp_gateway` | `8080` | `async_mcp_gateway` |
| `hydra_engine` | `8081` | `hydra_engine` |
| `hydra_engine_worker` | none | `hydra_engine_worker` |
| `synapse_mesh` | `8082` | `synapse_mesh` |
| `swarm_bus` | `8085` | `swarm_bus` |
| `spatial_flux` | `8084` | `spatial_flux` |

## Validation Commands

```bash
uv run ruff check .
uv run mypy agent_platform_os scripts tests
uv run pytest -q
docker compose config --quiet
```

## Operational Notes

PostgreSQL uses a named volume at `postgres_prime_data`. Redis uses append-only persistence in
`redis_stream_data` to preserve Redis Streams state across restarts. `docker compose down` stops
containers without deleting state; `docker compose down -v` deletes the named volumes and should
only be used for intentional local resets.
