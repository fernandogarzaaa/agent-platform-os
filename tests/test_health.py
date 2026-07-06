"""Tests for root health target construction."""

from __future__ import annotations

from agent_platform_os.config import PlatformSettings
from agent_platform_os.health import TargetKind, build_targets, host_port_from_url


def test_host_port_from_url_uses_default_port_when_missing() -> None:
    assert host_port_from_url("redis://redis_broker/0", 6379) == ("redis_broker", 6379)


def test_build_targets_maps_service_ports_and_health_paths() -> None:
    settings = PlatformSettings(
        POSTGRES_PRIME_URL="postgresql://user:pass@postgres_db:5432/db",
        REDIS_STREAM_URL="redis://redis_broker:6379/0",
        GATEWAY_PORT=18080,
        HYDRA_PORT=18081,
        SYNAPSE_PORT=18082,
        SWARMBUS_PORT=18083,
        SPATIAL_FLUX_PORT=18084,
    )
    targets = {target.name: target for target in build_targets(settings)}

    assert targets["postgres_db"].kind is TargetKind.TCP
    assert targets["redis_broker"].kind is TargetKind.REDIS
    assert targets["async_mcp_gateway"].port == 18080
    assert targets["spatial_flux"].path == "/v1/spatial/telemetry"
