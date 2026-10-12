"""Clone or update the five Agent Platform OS service repositories.

Each checkout is pinned to the ref in the service catalog (a commit SHA by
default). Override one with ``<SERVICE_NAME>_REF``, e.g. ``SWARM_BUS_REF=main``.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent_platform_os.catalog import SERVICE_DEFINITIONS, ServiceDefinition  # noqa: E402


def run_command(command: list[str], cwd: Path | None = None) -> None:
    """Run a subprocess command with explicit failure propagation."""
    completed = subprocess.run(command, cwd=cwd, text=True, check=False)
    if completed.returncode != 0:
        joined = " ".join(command)
        raise RuntimeError(f"command failed with exit code {completed.returncode}: {joined}")


def service_ref(service: ServiceDefinition) -> str:
    """Return the git ref to check out: env override, else the catalog pin."""
    override = os.environ.get(f"{service.name.upper()}_REF", "").strip()
    return override or service.ref


def ref_exists(target: Path, ref: str) -> bool:
    """True when ``ref`` resolves to a commit in the checkout."""
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def checkout_ref(target: Path, ref: str) -> None:
    """Check out ``ref`` detached; branch names resolve to ``origin/<branch>``."""
    if ref.startswith("-"):
        raise ValueError(f"invalid git ref {ref!r}")
    remote_branch = f"origin/{ref}"
    resolved = remote_branch if ref_exists(target, remote_branch) else ref
    run_command(["git", "checkout", "--quiet", "--detach", resolved], cwd=target)


def clone_service(root: Path, service: ServiceDefinition) -> None:
    """Clone a service repository and check out its pinned ref."""
    target = root / service.checkout_path
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        print(f"service_exists name={service.name} path={target}")
        return
    ref = service_ref(service)
    run_command(["git", "clone", service.repository, str(target)])
    checkout_ref(target, ref)
    print(f"service_cloned name={service.name} path={target} ref={ref}")


def update_service(root: Path, service: ServiceDefinition) -> None:
    """Fetch an existing service checkout and move it to its pinned ref."""
    target = root / service.checkout_path
    if not target.exists():
        clone_service(root, service)
        return
    ref = service_ref(service)
    run_command(["git", "fetch", "--prune", "--tags", "origin"], cwd=target)
    checkout_ref(target, ref)
    print(f"service_updated name={service.name} path={target} ref={ref}")


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
        help="Fetch existing service checkouts and move them to their pinned refs.",
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
