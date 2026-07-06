"""Tests for the Agent Platform OS service catalog."""

from __future__ import annotations

import pytest

from agent_platform_os.catalog import SERVICE_DEFINITIONS, get_service


def test_catalog_contains_all_five_platform_services() -> None:
    expected = {
        "async_mcp_gateway",
        "hydra_engine",
        "synapse_mesh",
        "swarm_bus",
        "spatial_flux",
    }
    assert set(SERVICE_DEFINITIONS) == expected


def test_get_service_rejects_unknown_service() -> None:
    with pytest.raises(ValueError, match="unknown service"):
        get_service("missing")
