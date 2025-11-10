"""
Integration tests for Load Balancer.
"""
import pytest

# Skip all tests if implementation doesn't exist yet
try:
    from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
    from load_balancer.balancer import create_app
    from load_balancer.server_pool import ServerPool
    HAS_IMPLEMENTATION = True
except ImportError:
    HAS_IMPLEMENTATION = False

pytestmark = pytest.mark.skipif(not HAS_IMPLEMENTATION, reason="Balancer implementation not available yet")


class TestLoadBalancer(AioHTTPTestCase):
    """Integration tests for load balancer."""
    
    async def get_application(self):
        """Create test application."""
        # No backends configured to simplify integration tests
        pool = ServerPool([])
        return create_app(pool)
    
    @unittest_run_loop
    async def test_returns_503_when_no_backends(self):
        """Requests should return 503 when no healthy backends are available."""
        resp = await self.client.request("GET", "/")
        assert resp.status == 503

