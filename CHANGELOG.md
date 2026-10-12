# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
