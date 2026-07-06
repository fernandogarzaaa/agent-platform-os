"""Clone or update the five Agent Platform OS service repositories."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from agent_platform_os.catalog import SERVICE_DEFINITIONS, ServiceDefinition


def run_command(command: list[str], cwd: Path | None = None) -> None:
    """Run a subprocess command with explicit failure propagation."""
    completed = subprocess.run(command, cwd=cwd, text=True, check=False)
    if completed.returncode != 0:
        joined = " ".join(command)
        raise RuntimeError(f"command failed with exit code {completed.returncode}: {joined}")


def clone_service(root: Path, service: ServiceDefinition) -> None:
    """Clone a service repository into its expected workspace path."""
    target = root / service.checkout_path
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        print(f"service_exists name={service.name} path={target}")
        return
    run_command(["git", "clone", service.repository, str(target)])
    print(f"service_cloned name={service.name} path={target}")


def update_service(root: Path, service: ServiceDefinition) -> None:
    """Fast-forward an existing service checkout."""
    target = root / service.checkout_path
    if not target.exists():
        clone_service(root, service)
        return
    run_command(["git", "fetch", "--prune", "origin"], cwd=target)
    run_command(["git", "pull", "--ff-only"], cwd=target)
    print(f"service_updated name={service.name} path={target}")


def selected_services(names: list[str]) -> list[ServiceDefinition]:
    """Resolve requested service names to definitions."""
    if not names:
        return list(SERVICE_DEFINITIONS.values())
    unknown = sorted(set(names) - set(SERVICE_DEFINITIONS))
    if unknown:
        known = ", ".join(sorted(SERVICE_DEFINITIONS))
        raise ValueError(f"unknown services {unknown}; expected one or more of: {known}")
    return [SERVICE_DEFINITIONS[name] for name in names]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=".",
        help="Agent Platform OS root directory. Defaults to the current directory.",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Fetch and fast-forward existing service checkouts.",
    )
    parser.add_argument(
        "services",
        nargs="*",
        help="Optional subset of service names to clone or update.",
    )
    return parser.parse_args()


def main() -> None:
    """Run service bootstrap operations."""
    args = parse_args()
    root = Path(args.root).resolve()
    try:
        services = selected_services(list(args.services))
        for service in services:
            if args.update:
                update_service(root, service)
            else:
                clone_service(root, service)
    except Exception as exc:
        print(f"bootstrap_failed detail={type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
