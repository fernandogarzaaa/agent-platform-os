"""Tests for the service launcher privilege drop and pinned bootstrap checkouts."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from agent_platform_os.catalog import SERVICE_DEFINITIONS, ServiceDefinition

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"_test_{name}", SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


run_service = load_script("run_service")
bootstrap = load_script("bootstrap_services")


def test_privilege_drop_clears_supplementary_groups_before_setgid_setuid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(run_service.os, "getuid", lambda: 0)
    monkeypatch.setattr(
        run_service.pwd,
        "getpwnam",
        lambda name: SimpleNamespace(pw_uid=1234, pw_gid=5678, pw_dir="/home/platform"),
    )
    monkeypatch.setattr(
        run_service, "run_checked", lambda command, cwd: calls.append(("run", command))
    )
    monkeypatch.setattr(
        run_service.os, "setgroups", lambda groups: calls.append(("setgroups", groups))
    )
    monkeypatch.setattr(run_service.os, "setgid", lambda gid: calls.append(("setgid", gid)))
    monkeypatch.setattr(run_service.os, "setuid", lambda uid: calls.append(("setuid", uid)))
    monkeypatch.setenv("UV_CACHE_DIR", str(tmp_path / "missing-cache"))

    run_service.drop_privileges_after_reconciling_ownership(tmp_path)

    drop_calls = [call for call in calls if call[0] != "run"]
    assert drop_calls == [("setgroups", []), ("setgid", 5678), ("setuid", 1234)]
    assert ("run", ["chown", "-R", "1234:5678", str(tmp_path)]) in calls
    assert run_service.os.environ["HOME"] == "/home/platform"


def test_privilege_drop_is_a_no_op_when_not_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(run_service.os, "getuid", lambda: 1000)

    def fail(*args: object) -> None:
        raise AssertionError("must not change identity when not root")

    monkeypatch.setattr(run_service.os, "setgroups", fail)
    monkeypatch.setattr(run_service.os, "setgid", fail)
    monkeypatch.setattr(run_service.os, "setuid", fail)

    run_service.drop_privileges_after_reconciling_ownership(tmp_path)


def test_every_service_is_pinned_to_a_commit() -> None:
    for service in SERVICE_DEFINITIONS.values():
        assert len(service.ref) == 40, service.name
        int(service.ref, 16)


def test_service_ref_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    service = SERVICE_DEFINITIONS["swarm_bus"]
    monkeypatch.delenv("SWARM_BUS_REF", raising=False)
    assert bootstrap.service_ref(service) == service.ref
    monkeypatch.setenv("SWARM_BUS_REF", "  v1.2.3 ")
    assert bootstrap.service_ref(service) == "v1.2.3"
    monkeypatch.setenv("SWARM_BUS_REF", "   ")
    assert bootstrap.service_ref(service) == service.ref


def git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return completed.stdout.strip()


@pytest.fixture()
def upstream(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "upstream"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    (repo / "f.txt").write_text("one")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "one")
    first = git(repo, "rev-parse", "HEAD")
    (repo / "f.txt").write_text("two")
    git(repo, "commit", "-q", "-am", "two")
    second = git(repo, "rev-parse", "HEAD")
    return repo, first, second


def make_service(repo: Path, ref: str) -> ServiceDefinition:
    return ServiceDefinition(
        name="demo_svc",
        repository=str(repo),
        checkout_path="services/demo_svc",
        port=9999,
        app_module="app.main:app",
        health_path="/health",
        requires_postgres=False,
        requires_redis=False,
        description="test",
        ref=ref,
    )


def test_clone_checks_out_the_pinned_commit_not_head(
    upstream: tuple[Path, str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, first, _second = upstream
    monkeypatch.delenv("DEMO_SVC_REF", raising=False)
    root = tmp_path / "platform"
    bootstrap.clone_service(root, make_service(repo, first))
    assert git(root / "services/demo_svc", "rev-parse", "HEAD") == first


def test_update_moves_to_the_pin_and_branch_override_tracks_origin(
    upstream: tuple[Path, str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, first, second = upstream
    root = tmp_path / "platform"
    monkeypatch.delenv("DEMO_SVC_REF", raising=False)
    bootstrap.clone_service(root, make_service(repo, second))
    checkout = root / "services/demo_svc"
    assert git(checkout, "rev-parse", "HEAD") == second

    bootstrap.update_service(root, make_service(repo, first))
    assert git(checkout, "rev-parse", "HEAD") == first

    (repo / "f.txt").write_text("three")
    git(repo, "commit", "-q", "-am", "three")
    third = git(repo, "rev-parse", "HEAD")
    monkeypatch.setenv("DEMO_SVC_REF", "main")
    bootstrap.update_service(root, make_service(repo, first))
    assert git(checkout, "rev-parse", "HEAD") == third


def test_checkout_rejects_option_like_refs(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="invalid git ref"):
        bootstrap.checkout_ref(tmp_path, "--orphan=x")


def test_unknown_pinned_ref_fails_loudly(upstream: tuple[Path, str, str], tmp_path: Path) -> None:
    repo, _first, _second = upstream
    with pytest.raises(RuntimeError, match="command failed"):
        bootstrap.clone_service(tmp_path / "platform", make_service(repo, "0" * 40))


def test_update_clones_a_missing_checkout_at_the_pin(
    upstream: tuple[Path, str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, first, _second = upstream
    monkeypatch.delenv("DEMO_SVC_REF", raising=False)
    root = tmp_path / "nested" / "platform"
    bootstrap.update_service(root, make_service(repo, first))
    assert git(root / "services/demo_svc", "rev-parse", "HEAD") == first


ALIAS_VARS = (
    "SWARMBUS_LOOP_DEPTH_LIMIT",
    "LOCK_LEASE_TTL_MS",
    "EVENT_REPLAY_RETRY_LIMIT",
    "MAX_LOOP_DEPTH",
    "LOCK_TTL_MS",
    "MAX_STEP_RETRIES",
)


@pytest.fixture()
def clean_alias_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in ALIAS_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.mark.parametrize("service", ["swarm_bus", "synapse_mesh"])
def test_platform_knobs_reach_bus_settings(
    clean_alias_env: pytest.MonkeyPatch, service: str
) -> None:
    clean_alias_env.setenv("SWARMBUS_LOOP_DEPTH_LIMIT", "32")
    clean_alias_env.setenv("LOCK_LEASE_TTL_MS", "30000")
    run_service.apply_environment_aliases(service, 8083)
    import os

    assert os.environ["MAX_LOOP_DEPTH"] == "32"
    assert os.environ["LOCK_TTL_MS"] == "30000"


def test_retry_limit_reaches_hydra(clean_alias_env: pytest.MonkeyPatch) -> None:
    clean_alias_env.setenv("EVENT_REPLAY_RETRY_LIMIT", "5")
    run_service.apply_environment_aliases("hydra_engine", 8081)
    import os

    assert os.environ["MAX_STEP_RETRIES"] == "5"
    assert "MAX_LOOP_DEPTH" not in os.environ


def test_explicit_service_setting_wins_over_platform_alias(
    clean_alias_env: pytest.MonkeyPatch,
) -> None:
    clean_alias_env.setenv("SWARMBUS_LOOP_DEPTH_LIMIT", "32")
    clean_alias_env.setenv("MAX_LOOP_DEPTH", "8")
    run_service.apply_environment_aliases("swarm_bus", 8083)
    import os

    assert os.environ["MAX_LOOP_DEPTH"] == "8"


def test_compose_publishes_ports_on_loopback_by_default() -> None:
    compose = (Path(__file__).resolve().parents[1] / "docker-compose.yml").read_text()
    published = [
        line.strip()
        for line in compose.splitlines()
        if line.strip().startswith('- "')
        and line.strip().endswith('"')
        and ":" in line
        and "/" not in line
    ]
    assert published, "expected published ports in docker-compose.yml"
    for line in published:
        assert line.startswith('- "${PLATFORM_BIND_ADDRESS:-127.0.0.1}:'), line
