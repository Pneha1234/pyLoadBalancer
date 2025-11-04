"""
Unit tests for ServerPool class.
"""
import pytest
from load_balancer.server_pool import ServerPool


class TestServerPool:
    """Test cases for ServerPool."""
    
    def test_initialization(self):
        """Test ServerPool initialization."""
        servers = ["http://localhost:9001", "http://localhost:9002"]
        pool = ServerPool(servers)
        assert len(pool) == 2
        assert pool.get_all_servers() == servers
    
    def test_round_robin_selection(self):
        """Test round-robin server selection."""
        servers = ["http://localhost:9001", "http://localhost:9002", "http://localhost:9003"]
        pool = ServerPool(servers)
        
        # Should cycle through servers
        assert pool.get_next_server() == servers[0]
        assert pool.get_next_server() == servers[1]
        assert pool.get_next_server() == servers[2]
        assert pool.get_next_server() == servers[0]  # Should wrap around
    
    def test_empty_pool(self):
        """Test behavior with empty server pool."""
        pool = ServerPool([])
        assert pool.get_next_server() is None
        assert len(pool) == 0
    
    def test_add_server(self):
        """Test adding a server to the pool."""
        pool = ServerPool(["http://localhost:9001"])
        pool.add_server("http://localhost:9002")
        assert len(pool) == 2
        assert "http://localhost:9002" in pool.get_all_servers()
    
    def test_remove_server(self):
        """Test removing a server from the pool."""
        servers = ["http://localhost:9001", "http://localhost:9002"]
        pool = ServerPool(servers)
        pool.remove_server("http://localhost:9001")
        assert len(pool) == 1
        assert "http://localhost:9001" not in pool.get_all_servers()
    
    @pytest.mark.asyncio
    async def test_async_server_selection(self):
        """Test async server selection with concurrency."""
        servers = ["http://localhost:9001", "http://localhost:9002"]
        pool = ServerPool(servers)
        
        # Simulate concurrent requests
        selected = await pool.get_next_server_async()
        assert selected in servers

