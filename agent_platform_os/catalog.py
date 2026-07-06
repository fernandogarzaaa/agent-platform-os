"""Service catalog for the Agent Platform OS workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class ServiceDefinition:
    """Runtime metadata for a coordinated platform service."""

    name: str
    repository: str
    checkout_path: str
    port: int
    app_module: str
    health_path: str
    requires_postgres: bool
    requires_redis: bool
    description: str


SERVICE_DEFINITIONS: Final[dict[str, ServiceDefinition]] = {
    "async_mcp_gateway": ServiceDefinition(
        name="async_mcp_gateway",
        repository="https://github.com/fernandogarzaaa/async-mcp-gateway.git",
        checkout_path="services/async_mcp_gateway",
        port=8080,
        app_module="app.main:app",
        health_path="/health",
        requires_postgres=True,
        requires_redis=True,
        description="Secure asynchronous MCP ingress, proxying, and rate-limiting gateway.",
    ),
    "hydra_engine": ServiceDefinition(
        name="hydra_engine",
        repository="https://github.com/fernandogarzaaa/hydra-engine.git",
        checkout_path="services/hydra_engine",
        port=8081,
        app_module="app.main:app",
        health_path="/health",
        requires_postgres=True,
        requires_redis=True,
        description="Durable agent execution engine with replayable PostgreSQL state.",
    ),
    "synapse_mesh": ServiceDefinition(
        name="synapse_mesh",
        repository="https://github.com/fernandogarzaaa/SynapseMesh.git",
        checkout_path="services/synapse_mesh",
        port=8082,
        app_module="app.main:app",
        health_path="/health",
        requires_postgres=True,
        requires_redis=False,
        description="Semantic capability and model-routing mesh with policy-aware decisions.",
    ),
    "swarm_bus": ServiceDefinition(
        name="swarm_bus",
        repository="https://github.com/fernandogarzaaa/swarm-bus.git",
        checkout_path="services/swarm_bus",
        port=8083,
        app_module="app.main:app",
        health_path="/health",
        requires_postgres=False,
        requires_redis=True,
        description="Redis Streams multi-agent event bus with task locking and loop isolation.",
    ),
    "spatial_flux": ServiceDefinition(
        name="spatial_flux",
        repository="https://github.com/fernandogarzaaa/Spatial-Flux.git",
        checkout_path="services/spatial_flux",
        port=8084,
        app_module="app.main:app",
        health_path="/v1/spatial/telemetry",
        requires_postgres=False,
        requires_redis=False,
        description="Edge video ingestion and drift-triggered cloud VLA dispatch fabric.",
    ),
}


def get_service(name: str) -> ServiceDefinition:
    """Return a service definition by stable service name."""
    try:
        return SERVICE_DEFINITIONS[name]
    except KeyError as exc:
        known_services = ", ".join(sorted(SERVICE_DEFINITIONS))
        raise ValueError(f"unknown service {name!r}; expected one of: {known_services}") from exc
