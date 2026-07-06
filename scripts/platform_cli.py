"""Operator CLI for controlling a local Agent Platform OS stack."""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_platform_os.config import settings  # noqa: E402
from agent_platform_os.health import HealthResult, check_all  # noqa: E402

MINIMAL_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////"
    "2wBDAf//////////////////////////////////////////////////////////////////////////////////////"
    "wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAH/"
    "xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAEFAqf/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAEDAQE/ASP/xAAUEQEAAAAAAAAA"
    "AAAAAAAAAAAA/9oACAECAQE/ASP/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAY/Al//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oA"
    "CAEBAAE/IV//2gAMAwEAAgADAAAAEP/EABQRAQAAAAAAAAAAAAAAAAAAABD/2gAIAQMBAT8QH//EABQRAQAAAAAAAAAAAAAAAAAAABD/"
    "2gAIAQIBAT8QH//EABQQAQAAAAAAAAAAAAAAAAAAABD/2gAIAQEAAT8QH//Z"
)


def _base_url(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


async def run_health() -> int:
    results = await check_all(settings)
    health_results: list[HealthResult] = []
    for result in results:
        if isinstance(result, BaseException):
            print(f"health_check_error {type(result).__name__}: {result}")
            return 1
        health_results.append(result)
    for result in health_results:
        status = "OK" if result.ok else "FAIL"
        print(
            f"{status} {result.target.name} "
            f"{result.target.host}:{result.target.port}{result.target.path} "
            f"{result.latency_ms:.1f}ms {result.detail}"
        )
    return 0 if all(result.ok for result in health_results) else 1


async def run_workflow_demo() -> int:
    payload = {
        "tenant_id": "demo-tenant",
        "steps": [
            {"prompt": "Plan a local smoke workflow"},
            {"tool": "swarm_bus", "arguments": {"topic": "agent-events"}},
            {"result_consumer": "operator"},
        ],
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{_base_url(settings.HYDRA_PORT)}/workflows/trigger",
            json=payload,
        )
        response.raise_for_status()
        workflow = response.json()
        workflow_id = workflow["id"]
        for _ in range(20):
            audit_response = await client.get(
                f"{_base_url(settings.HYDRA_PORT)}/workflows/{workflow_id}/audit"
            )
            audit_response.raise_for_status()
            audit = audit_response.json()
            if audit["status"] in {"COMPLETED", "FAILED"}:
                print_json(audit)
                return 0 if audit["status"] == "COMPLETED" else 1
            await anyio_sleep(0.5)
        print_json({"workflow": workflow, "status": "timed_out_waiting_for_worker"})
        return 1


async def run_bus_demo() -> int:
    payload = {
        "task": "operator-cli-demo",
        "topic": "agent-events",
        "payload": {"message": "hello from platform_cli"},
        "history": [{"from": "operator", "to": "bus", "revision": 1}],
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{_base_url(settings.SWARMBUS_PORT)}/v1/bus/broadcast",
            json=payload,
        )
        response.raise_for_status()
        print_json(response.json())
    return 0


async def run_spatial_demo() -> int:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{_base_url(settings.SPATIAL_FLUX_PORT)}/v1/spatial/ingest",
            files={"file": ("demo.jpg", MINIMAL_JPEG, "image/jpeg")},
        )
        response.raise_for_status()
        print_json(response.json())
    return 0


async def anyio_sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("health", help="Check the local platform services.")
    subcommands.add_parser("workflow-demo", help="Run a Hydra workflow through the worker.")
    subcommands.add_parser("bus-demo", help="Publish one SwarmBus event.")
    subcommands.add_parser("spatial-demo", help="Send one demo frame through SpatialFlux.")
    return parser.parse_args()


def main() -> None:
    import asyncio

    args = parse_args()
    command = str(args.command)
    if command == "health":
        exit_code = asyncio.run(run_health())
    elif command == "workflow-demo":
        exit_code = asyncio.run(run_workflow_demo())
    elif command == "bus-demo":
        exit_code = asyncio.run(run_bus_demo())
    elif command == "spatial-demo":
        exit_code = asyncio.run(run_spatial_demo())
    else:
        raise ValueError(f"unknown command: {command}")
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
