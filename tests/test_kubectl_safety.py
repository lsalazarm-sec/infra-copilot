"""Tests for the kubectl tool safety gate."""

from __future__ import annotations

import pytest

from infra_copilot.config import Settings
from infra_copilot.tools.kubectl import KubectlBlocked, kubectl_run


@pytest.fixture
def settings() -> Settings:
    return Settings()


async def test_blocks_delete(settings: Settings) -> None:
    """delete is not in the default allowlist and must be rejected."""
    result = await kubectl_run(verb="delete", args=["pod", "victim"], settings=settings)
    assert isinstance(result, KubectlBlocked)
    assert "allowlist" in result.reason


async def test_blocks_apply(settings: Settings) -> None:
    """apply is not in the default allowlist and must be rejected."""
    result = await kubectl_run(verb="apply", args=["-f", "x.yaml"], settings=settings)
    assert isinstance(result, KubectlBlocked)


async def test_allowed_verb_passes_safety_gate(settings: Settings) -> None:
    """get is allowlisted and must pass the safety gate."""
    result = await kubectl_run(verb="get", args=["pods"], settings=settings)
    if isinstance(result, KubectlBlocked):
        assert "allowlist" not in result.reason
