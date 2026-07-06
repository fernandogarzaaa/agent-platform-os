"""Async health probes for Agent Platform OS."""

from __future__ import annotations

import asyncio
import socket
import time
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

import httpx

from agent_platform_os.catalog import SERVICE_DEFINITIONS
from agent_platform_os.config import PlatformSettings


class TargetKind(str, Enum):
    """Supported health target protocols."""

    TCP = "tcp"
    REDIS = "redis"
    HTTP = "http"


@dataclass(frozen=True, slots=True)
class HealthTarget:
    """A network component checked by the health verifier."""

    name: str
    kind: TargetKind
    host: str
    port: int
    path: str = "/health"


@dataclass(frozen=True, slots=True)
class HealthResult:
    """Result emitted by a single health probe."""

    target: HealthTarget
    ok: bool
    latency_ms: float
    detail: str


def host_port_from_url(value: str, default_port: int) -> tuple[str, int]:
    """Extract host and port from a database or cache URL."""
    parsed = urlparse(value)
    if parsed.hostname is None:
        raise ValueError(f"URL does not contain a hostname: {value}")
    return parsed.hostname, parsed.port or default_port


def build_targets(settings: PlatformSettings) -> list[HealthTarget]:
    """Build health targets from the validated environment settings."""
    postgres_host, postgres_port = host_port_from_url(settings.POSTGRES_PRIME_URL, 5432)
    redis_host, redis_port = host_port_from_url(settings.REDIS_STREAM_URL, 6379)
    service_ports = {
        "async_mcp_gateway": settings.GATEWAY_PORT,
        "hydra_engine": settings.HYDRA_PORT,
        "synapse_mesh": settings.SYNAPSE_PORT,
        "swarm_bus": settings.SWARMBUS_PORT,
        "spatial_flux": settings.SPATIAL_FLUX_PORT,
    }

    targets = [
        HealthTarget("postgres_db", TargetKind.TCP, postgres_host, postgres_port),
        HealthTarget("redis_broker", TargetKind.REDIS, redis_host, redis_port),
    ]
    for service_name, definition in SERVICE_DEFINITIONS.items():
        targets.append(
            HealthTarget(
                name=service_name,
                kind=TargetKind.HTTP,
                host="127.0.0.1",
                port=service_ports[service_name],
                path=definition.health_path,
            )
        )
    return targets


async def check_tcp(target: HealthTarget, timeout_seconds: float) -> HealthResult:
    """Open and close a TCP connection to prove reachability."""
    start = time.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(target.host, target.port),
            timeout=timeout_seconds,
        )
        reader.feed_eof()
        writer.close()
        await writer.wait_closed()
        return HealthResult(target, True, (time.perf_counter() - start) * 1000, "tcp accepted")
    except (OSError, TimeoutError, socket.gaierror) as exc:
        return HealthResult(
            target,
            False,
            (time.perf_counter() - start) * 1000,
            f"{type(exc).__name__}: {exc}",
        )


async def check_redis(target: HealthTarget, timeout_seconds: float) -> HealthResult:
    """Send a raw Redis RESP PING command and require PONG."""
    start = time.perf_counter()
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(target.host, target.port),
            timeout=timeout_seconds,
        )
        reader = _reader
        writer.write(b"*1\r\n$4\r\nPING\r\n")
        await writer.drain()
        response = await asyncio.wait_for(reader.read(16), timeout=timeout_seconds)
        writer.close()
        await writer.wait_closed()
        latency_ms = (time.perf_counter() - start) * 1000
        if response.startswith(b"+PONG"):
            return HealthResult(target, True, latency_ms, "redis PONG")
        return HealthResult(target, False, latency_ms, f"unexpected redis response: {response!r}")
    except (OSError, TimeoutError, socket.gaierror) as exc:
        return HealthResult(
            target,
            False,
            (time.perf_counter() - start) * 1000,
            f"{type(exc).__name__}: {exc}",
        )


async def check_http(target: HealthTarget, client: httpx.AsyncClient) -> HealthResult:
    """Check an HTTP service health endpoint."""
    start = time.perf_counter()
    url = f"http://{target.host}:{target.port}{target.path}"
    try:
        response = await client.get(url)
        latency_ms = (time.perf_counter() - start) * 1000
        if 200 <= response.status_code < 300:
            return HealthResult(target, True, latency_ms, f"http {response.status_code}")
        detail = f"http {response.status_code}: {response.text[:200]}"
        return HealthResult(target, False, latency_ms, detail)
    except httpx.HTTPError as exc:
        return HealthResult(
            target,
            False,
            (time.perf_counter() - start) * 1000,
            f"{type(exc).__name__}: {exc}",
        )


async def check_target(
    target: HealthTarget,
    client: httpx.AsyncClient,
    timeout_seconds: float,
) -> HealthResult:
    """Dispatch a health target to its protocol checker."""
    if target.kind is TargetKind.TCP:
        return await check_tcp(target, timeout_seconds)
    if target.kind is TargetKind.REDIS:
        return await check_redis(target, timeout_seconds)
    if target.kind is TargetKind.HTTP:
        return await check_http(target, client)
    return HealthResult(target, False, 0.0, f"unsupported target kind: {target.kind}")


async def check_all(settings: PlatformSettings) -> list[HealthResult | BaseException]:
    """Run all configured health checks concurrently."""
    targets = build_targets(settings)
    timeout = httpx.Timeout(settings.HEALTH_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout) as client:
        results = await asyncio.gather(
            *(check_target(target, client, settings.HEALTH_TIMEOUT_SECONDS) for target in targets),
            return_exceptions=True,
        )
    return list(results)
