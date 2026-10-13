# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-10-13

### Security
- docker compose publishes every port on `PLATFORM_BIND_ADDRESS` (default `127.0.0.1`)
  instead of all interfaces. Previously Postgres (password `agent_platform`), Redis (no
  auth) and every service API were reachable from the network on a default install.
  Set `PLATFORM_BIND_ADDRESS=0.0.0.0` to restore the old behaviour.
- `HYDRA_API_KEY`, `SYNAPSEMESH_API_KEY` and `SWARMBUS_API_KEY` are passed through to the
  services (empty by default = unchanged) so their API-key gates can be switched on from `.env`.

### Fixed
- `SWARMBUS_LOOP_DEPTH_LIMIT`, `LOCK_LEASE_TTL_MS` and `EVENT_REPLAY_RETRY_LIMIT` had no
  effect: the services read `MAX_LOOP_DEPTH`, `LOCK_TTL_MS` and `MAX_STEP_RETRIES`, so the
  bus ran with loop depth 4 / 10 s leases instead of the configured 32 / 30 s. The launcher
  now aliases them (an explicitly set service variable still wins).

### Changed
- Service pins: hydra-engine v0.1.1 (`82b7c08`, lease fencing), SynapseMesh v0.1.1
  (`d4ba799`, optional API key, VLA input validation), swarm-bus v0.1.0 (`658d9c1`,
  lease renew/release endpoints).

## [1.0.1] - 2026-10-13

First tagged release.

### Security
- `scripts/run_service.py` clears supplementary groups (`os.setgroups([])`) before
  `setgid`/`setuid`, so the dropped-privilege process no longer keeps root's groups.
- Service checkouts are pinned: every `ServiceDefinition` carries a `ref` (commit SHA);
  bootstrap clones/updates check out the pin detached, `<SERVICE_NAME>_REF` overrides it,
  and refs starting with `-` are rejected.

### Changed
- Pins bumped to the first tagged service releases: async-mcp-gateway v0.1.0 (`51500aa`;
  no failover on provider 4xx, safe CORS) and Spatial-Flux v1.0.0 (`0ab5ff2`).

### Added / Changed
- Dependabot config for pip, Docker and GitHub Actions (weekly)
- SECURITY.md with private reporting contact
