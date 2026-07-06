"""One-command installer for Agent Platform OS and its service repositories."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT_REPOSITORY_URL = "https://github.com/fernandogarzaaa/agent-platform-os.git"


@dataclass(frozen=True, slots=True)
class ServiceRepository:
    """Repository checkout required by the platform runtime."""

    name: str
    repository_url: str
    checkout_path: str


SERVICE_REPOSITORIES = (
    ServiceRepository(
        name="async_mcp_gateway",
        repository_url="https://github.com/fernandogarzaaa/async-mcp-gateway.git",
        checkout_path="services/async_mcp_gateway",
    ),
    ServiceRepository(
        name="hydra_engine",
        repository_url="https://github.com/fernandogarzaaa/hydra-engine.git",
        checkout_path="services/hydra_engine",
    ),
    ServiceRepository(
        name="synapse_mesh",
        repository_url="https://github.com/fernandogarzaaa/SynapseMesh.git",
        checkout_path="services/synapse_mesh",
    ),
    ServiceRepository(
        name="swarm_bus",
        repository_url="https://github.com/fernandogarzaaa/swarm-bus.git",
        checkout_path="services/swarm_bus",
    ),
    ServiceRepository(
        name="spatial_flux",
        repository_url="https://github.com/fernandogarzaaa/Spatial-Flux.git",
        checkout_path="services/spatial_flux",
    ),
)


def run_command(command: list[str], cwd: Path | None = None) -> None:
    """Run a command and raise with context on failure."""
    print(f"running command={' '.join(command)} cwd={cwd or Path.cwd()}", flush=True)
    completed = subprocess.run(command, cwd=cwd, check=False)
    if completed.returncode != 0:
        joined = " ".join(command)
        raise RuntimeError(f"command failed with exit code {completed.returncode}: {joined}")


def require_executable(name: str) -> None:
    """Require a command-line executable to be available on PATH."""
    if shutil.which(name) is None:
        raise RuntimeError(f"required executable is missing from PATH: {name}")


def is_platform_root(path: Path) -> bool:
    """Return whether a directory looks like an Agent Platform OS root checkout."""
    return (
        (path / "pyproject.toml").exists()
        and (path / "agent_platform_os").is_dir()
        and (path / "scripts").is_dir()
    )


def clone_or_update_repository(
    repository_url: str,
    target: Path,
    branch: str,
    update: bool,
) -> None:
    """Clone a repository or optionally fast-forward an existing checkout."""
    if target.exists():
        if not (target / ".git").exists():
            raise RuntimeError(f"target exists but is not a git checkout: {target}")
        if update:
            run_command(["git", "fetch", "--prune", "origin"], cwd=target)
            run_command(["git", "checkout", branch], cwd=target)
            run_command(["git", "pull", "--ff-only", "origin", branch], cwd=target)
            print(f"repository_updated path={target}", flush=True)
        else:
            print(f"repository_exists path={target}", flush=True)
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    run_command(["git", "clone", "--branch", branch, repository_url, str(target)])
    print(f"repository_cloned path={target}", flush=True)


def prepare_root(target: Path, branch: str, update: bool) -> Path:
    """Ensure the root platform repository exists and return its path."""
    cwd = Path.cwd().resolve()
    if is_platform_root(cwd):
        if update and (cwd / ".git").exists():
            run_command(["git", "fetch", "--prune", "origin"], cwd=cwd)
            run_command(["git", "checkout", branch], cwd=cwd)
            run_command(["git", "pull", "--ff-only", "origin", branch], cwd=cwd)
        print(f"using_existing_platform_root path={cwd}", flush=True)
        return cwd
    clone_or_update_repository(ROOT_REPOSITORY_URL, target.resolve(), branch, update)
    root = target.resolve()
    if not is_platform_root(root):
        raise RuntimeError(f"cloned repository is not a valid platform root: {root}")
    return root


def ensure_env_file(root: Path, overwrite: bool) -> None:
    """Create .env from .env.example when needed."""
    env_example = root / ".env.example"
    env_file = root / ".env"
    if not env_example.exists():
        raise FileNotFoundError(f"missing environment manifest: {env_example}")
    if env_file.exists() and not overwrite:
        print(f"env_exists path={env_file}", flush=True)
        return
    shutil.copyfile(env_example, env_file)
    print(f"env_created path={env_file}", flush=True)


def install_services(root: Path, branch: str, update: bool) -> None:
    """Clone or update all service repositories required by the platform."""
    for service in SERVICE_REPOSITORIES:
        clone_or_update_repository(
            repository_url=service.repository_url,
            target=root / service.checkout_path,
            branch=branch,
            update=update,
        )


def sync_root(root: Path, skip_uv_sync: bool) -> None:
    """Synchronize the root workspace when uv is installed."""
    if skip_uv_sync:
        print("uv_sync_skipped reason=operator_request", flush=True)
        return
    if shutil.which("uv") is None:
        print("uv_sync_skipped reason=uv_not_found", flush=True)
        return
    run_command(["uv", "sync", "--extra", "dev"], cwd=root)


def parse_args() -> argparse.Namespace:
    """Parse installer arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        default="agent-platform-os",
        help="Directory for the root platform checkout when the installer is run outside the repo.",
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Git branch to clone for the root and service repositories.",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Fast-forward existing root and service checkouts.",
    )
    parser.add_argument(
        "--overwrite-env",
        action="store_true",
        help="Replace an existing .env file with .env.example.",
    )
    parser.add_argument(
        "--skip-uv-sync",
        action="store_true",
        help="Skip root uv dependency synchronization.",
    )
    return parser.parse_args()


def main() -> None:
    """Install the root platform and all required service repositories."""
    args = parse_args()
    try:
        require_executable("git")
        root = prepare_root(Path(args.target), str(args.branch), bool(args.update))
        ensure_env_file(root, overwrite=bool(args.overwrite_env))
        install_services(root, branch=str(args.branch), update=bool(args.update))
        sync_root(root, skip_uv_sync=bool(args.skip_uv_sync))
        print(f"install_complete platform_root={root}", flush=True)
    except Exception as exc:
        print(f"install_failed detail={type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
