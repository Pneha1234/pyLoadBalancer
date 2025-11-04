"""
Integration tests for Load Balancer.
"""
import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from load_balancer.balancer import create_balancer_app
from load_balancer.server_pool import ServerPool


class TestLoadBalancer(AioHTTPTestCase):
    """Integration tests for load balancer."""
    
    async def get_application(self):
        """Create test application."""
        # Mock backend servers
        servers = ["http://localhost:9001", "http://localhost:9002"]
        pool = ServerPool(servers)
        return create_balancer_app(pool)
    
    @unittest_run_loop
    async def test_health_endpoint(self):
        """Test load balancer health endpoint."""
        resp = await self.client.request("GET", "/health")
        assert resp.status == 200
    
    @unittest_run_loop
    async def test_request_forwarding(self):
        """Test request forwarding to backend."""
        # This test requires running backend servers
        # Mock the backend response or use aiohttp test server
        pass

