# Agent Platform OS

Agent Platform OS is the production root control plane for a five-service AI operations
fabric. It provides the workspace contract, service catalog, environment validation, Docker
orchestration, bootstrap automation, and health verification needed to run the platform as one
coordinated system.

The root repository does not duplicate service business logic. Each service remains an
independent Python package under `services/*`, while this repository owns the runtime contract
that lets them operate together.

## Completion Boundary

This repository is complete as the root Agent Platform OS control plane. It includes the typed
root package, environment contract, service catalog, bootstrap automation, container launcher,
Docker Compose fabric, health verification suite, CI workflow, tests, and operations
documentation.

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
| `synapse_mesh` | [`fernandogarzaaa/SynapseMesh`](https://github.com/fernandogarzaaa/SynapseMesh) | Semantic model and capability routing with policy-aware fallback. |
| `swarm_bus` | [`fernandogarzaaa/swarm-bus`](https://github.com/fernandogarzaaa/swarm-bus) | Redis Streams event bus with atomic task locking and loop isolation. |
| `spatial_flux` | [`fernandogarzaaa/Spatial-Flux`](https://github.com/fernandogarzaaa/Spatial-Flux) | Edge video ingestion and structural-drift-triggered cloud VLA routing. |

## Architecture

```text
                            +----------------------+
                            |     user ingress     |
                            +----------+-----------+
                                       |
                                       v
                              +------------------+
                              | async_mcp_gateway|
                              | zero-trust edge  |
                              +--------+---------+
                                       |
            +--------------------------+--------------------------+
            |                                                     |
            v                                                     v
    +---------------+                                     +---------------+
    |  hydra_engine | <------ durable event state ------> |  PostgreSQL   |
    | crash replay  |                                     | state memory  |
    +-------+-------+                                     +---------------+
            |
            v
    +---------------+        selected model/action        +---------------+
    | synapse_mesh  | ----------------------------------> | provider APIs |
    | optimization  |                                     +---------------+
    +-------+-------+
            |
            v
    +---------------+        task envelopes               +---------------+
    |  swarm_bus    | <---------------------------------> | Redis Streams |
    | coordination  |                                     +---------------+
    +-------+-------+
            ^
            |
    metadata heartbeats and anomaly events
            |
    +---------------+        high-drift frame uploads     +---------------+
    | spatial_flux  | ----------------------------------> | cloud VLA     |
    | edge vision   |                                     +---------------+
    +---------------+
```

## Production Invariants

### Zero-Trust Identity Resolution

All public user and tool ingress is routed through `async_mcp_gateway`. The gateway evaluates
tenant identity, compliance posture, token budgets, and stream safety before requests can reach
model routing or durable execution paths.

### Deterministic State Recovery

`hydra_engine` persists execution state in PostgreSQL and replays failed event journals using
bounded retry limits. Recovery is based on durable step records, not reconstructed process logs.

### Bandwidth Containment

`spatial_flux` performs structural drift analysis at the edge. Nominal frames remain local and
emit metadata heartbeats; only anomalous frames are compressed and routed to cloud VLA systems.

### Graph-Cycle Failure Isolation

`swarm_bus` treats agent handoffs as a graph. Loop depth limits and Redis lock leases isolate
runaway coordination cycles before they consume execution capacity indefinitely.

## Repository Layout

```text
agent-platform-os/
├── agent_platform_os/          # typed root orchestration package
├── scripts/
│   ├── bootstrap_services.py   # clone or fast-forward service repos
│   ├── check_health.py         # async platform health verifier
│   └── run_service.py          # container service launcher
├── tests/                      # root package and health target tests
├── .github/workflows/ci.yml    # CI validation gate
├── .env.example                # complete environment manifest
├── docker-compose.yml          # production-oriented local fabric
├── Dockerfile                  # hardened root service launcher image
└── pyproject.toml              # uv workspace and lint/type config
```

Service checkouts are intentionally ignored by Git and should live at:

```text
services/async_mcp_gateway
services/hydra_engine
services/synapse_mesh
services/swarm_bus
services/spatial_flux
```

## Bootstrap

Install root dependencies:

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

Fast-forward existing service checkouts:

```bash
uv run python scripts/bootstrap_services.py --update
```

Start the platform:

```bash
docker compose up --build -d
```

Run health verification:

```bash
uv run python scripts/check_health.py
```

## Runtime Behavior

The Compose fabric starts PostgreSQL and Redis first, waits for their health checks, and then
starts service containers. Each service container mounts its corresponding `services/*` checkout,
validates that `pyproject.toml` and `app/main.py` are present, synchronizes dependencies with
`uv`, and launches the FastAPI app with `uvicorn app.main:app`.

This is a real launcher path. If a service checkout is absent or malformed, the container exits
with a clear error instead of idling.

## Port Map

| Component | Host Port | Internal DNS |
| --- | ---: | --- |
| PostgreSQL | `5432` | `postgres_db` |
| Redis | `6379` | `redis_broker` |
| `async_mcp_gateway` | `8080` | `async_mcp_gateway` |
| `hydra_engine` | `8081` | `hydra_engine` |
| `synapse_mesh` | `8082` | `synapse_mesh` |
| `swarm_bus` | `8083` | `swarm_bus` |
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
