"""
Tests for HealthChecker logic.
"""
from unittest.mock import AsyncMock

import pytest

from load_balancer.server_pool import ServerPool
from load_balancer.utils.health_checker import HealthChecker


@pytest.fixture
def server_pool() -> ServerPool:
    return ServerPool(["http://localhost:9001"])


@pytest.fixture
def health_checker(server_pool: ServerPool) -> HealthChecker:
    return HealthChecker(
        server_pool=server_pool,
        interval=0.1,
        timeout=0.1,
        path="/health",
        method="GET",
        expected_status=200,
        healthy_threshold=1,
        unhealthy_threshold=1,
    )


@pytest.mark.asyncio
async def test_marks_server_unhealthy_after_failure(
    server_pool: ServerPool, health_checker: HealthChecker
) -> None:
    """Servers should be removed from rotation after failing health checks."""
    probe_mock = AsyncMock(return_value=False)
    health_checker._probe = probe_mock  # type: ignore[attr-defined]

    await health_checker._check_server("http://localhost:9001")

    assert server_pool.is_healthy("http://localhost:9001") is False
    assert await server_pool.get_healthy_server_snapshot() == []
    probe_mock.assert_awaited()


@pytest.mark.asyncio
async def test_marks_server_healthy_after_recovery(
    server_pool: ServerPool, health_checker: HealthChecker
) -> None:
    """Recovered servers should return to healthy rotation."""
    await server_pool.mark_unhealthy("http://localhost:9001")
    assert await server_pool.get_healthy_server_snapshot() == []

    probe_mock = AsyncMock(return_value=True)
    health_checker._probe = probe_mock  # type: ignore[attr-defined]

    await health_checker._check_server("http://localhost:9001")

    assert server_pool.is_healthy("http://localhost:9001") is True
    healthy_servers = await server_pool.get_healthy_server_snapshot()
    assert healthy_servers == ["http://localhost:9001"]
    probe_mock.assert_awaited()

