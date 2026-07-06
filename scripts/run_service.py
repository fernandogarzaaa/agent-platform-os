"""Production container launcher for a mounted Agent Platform OS service."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from agent_platform_os.catalog import get_service


def require_service_directory(path: Path) -> None:
    """Validate that a mounted service checkout is runnable."""
    if not path.exists():
        raise FileNotFoundError(f"service directory does not exist: {path}")
    if not (path / "pyproject.toml").exists():
        raise FileNotFoundError(f"service pyproject.toml is missing: {path / 'pyproject.toml'}")
    if not (path / "app" / "main.py").exists():
        entrypoint = path / "app" / "main.py"
        raise FileNotFoundError(f"service FastAPI entrypoint is missing: {entrypoint}")


def apply_environment_aliases(service_name: str, port: int) -> None:
    """Expose root environment variables under common service-specific aliases."""
    os.environ.setdefault("APP_HOST", "0.0.0.0")
    os.environ.setdefault("APP_PORT", str(port))
    os.environ.setdefault("PORT", str(port))
    os.environ.setdefault("SERVICE_NAME", service_name)

    postgres_url = os.environ.get("POSTGRES_PRIME_URL")
    redis_url = os.environ.get("REDIS_STREAM_URL")
    if postgres_url:
        async_postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        os.environ.setdefault("DATABASE_URL", async_postgres_url)
        os.environ.setdefault("POSTGRES_URL", postgres_url)
    if redis_url:
        os.environ.setdefault("REDIS_URL", redis_url)
        os.environ.setdefault("REDIS_URI", redis_url)

    if service_name == "spatial_flux":
        os.environ.setdefault(
            "DRIFT_THRESHOLD",
            os.environ.get("EDGE_DRIFT_THRESHOLD", "0.15"),
        )
        os.environ.setdefault(
            "EDGE_COMPRESSION_QUALITY",
            os.environ.get("IMCODEC_QUALITY_RATIO", "80"),
        )
        os.environ.setdefault(
            "CLOUD_VLA_ENDPOINT_URL",
            os.environ.get("CLOUD_VLA_ENDPOINT_URL", "http://synapse_mesh:8082/v1/vla/commands"),
        )


def run_checked(command: list[str], cwd: Path) -> None:
    """Run a setup command and fail with context if it exits non-zero."""
    completed = subprocess.run(command, cwd=cwd, check=False)
    if completed.returncode != 0:
        joined = " ".join(command)
        raise RuntimeError(f"command failed with exit code {completed.returncode}: {joined}")


def sync_dependencies(service_dir: Path) -> None:
    """Synchronize service dependencies into the container environment."""
    command = ["uv", "sync", "--active"]
    if (service_dir / "uv.lock").exists():
        command.append("--frozen")
    run_checked(command, cwd=service_dir)


def exec_uvicorn(service_dir: Path, app_module: str, port: int) -> None:
    """Replace this process with uvicorn serving the selected app."""
    host = os.environ.get("APP_HOST", "0.0.0.0")
    workers = os.environ.get("WEB_CONCURRENCY", "1")
    args = [
        "uv",
        "run",
        "uvicorn",
        app_module,
        "--host",
        host,
        "--port",
        str(port),
        "--workers",
        workers,
        "--proxy-headers",
    ]
    os.chdir(service_dir)
    os.execvp(args[0], args)


def exec_module(service_dir: Path, module_name: str) -> None:
    """Replace this process with a Python module running inside the service env."""
    args = ["uv", "run", "python", "-m", module_name]
    os.chdir(service_dir)
    os.execvp(args[0], args)


def main() -> None:
    """Validate, sync, and launch the configured service."""
    service_name = os.environ.get("SERVICE_NAME")
    if not service_name:
        print("SERVICE_NAME is required", file=sys.stderr)
        sys.exit(1)
    try:
        definition = get_service(service_name)
        service_dir = Path(os.environ.get("SERVICE_DIR", "/workspace")).resolve()
        require_service_directory(service_dir)
        apply_environment_aliases(service_name, definition.port)
        sync_dependencies(service_dir)
        if os.environ.get("SERVICE_PROCESS") == "worker":
            worker_module = os.environ.get("SERVICE_WORKER_MODULE", "app.worker_main")
            exec_module(service_dir=service_dir, module_name=worker_module)
        exec_uvicorn(
            service_dir=service_dir,
            app_module=os.environ.get("SERVICE_APP_MODULE", definition.app_module),
            port=int(os.environ.get("PORT", str(definition.port))),
        )
    except Exception as exc:
        print(f"service_launch_failed service={service_name} detail={type(exc).__name__}: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
