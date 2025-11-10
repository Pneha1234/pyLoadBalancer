"""
Server pool management with round-robin load balancing.
"""
import asyncio
import contextlib
from collections import deque
from typing import Dict, List, Optional


class ServerPool:
    """
    Manages a pool of backend servers and implements round-robin selection.
    """
    
    def __init__(self, servers: List[str]):
        """
        Initialize the server pool.
        
        Args:
            servers: List of backend server URLs
        """
        # Convert list to deque for efficient rotation (healthy servers only)
        self._healthy_servers = deque(servers)
        # Track health status for all known servers
        self._server_health: Dict[str, bool] = {server: True for server in servers}
        # Use asyncio.Lock for thread-safe async operations
        self._lock = asyncio.Lock()
        
    def get_next_server(self) -> Optional[str]:
        """
        Get the next server using round-robin algorithm.
        
        Returns:
            URL of the next server, or None if no servers available
        """
        if not self._healthy_servers:
            return None
            
        # Rotate the queue to get next server
        # rotate(-1) moves first element to end (circular rotation)
        server = self._healthy_servers[0]
        self._healthy_servers.rotate(-1)
        return server
    
    async def get_next_server_async(self) -> Optional[str]:
        """
        Thread-safe async version of get_next_server.
        
        Returns:
            URL of the next server, or None if no servers available
        """
        async with self._lock:
            if not self._healthy_servers:
                return None

            server = self._healthy_servers[0]
            self._healthy_servers.rotate(-1)
            return server

    def add_server(self, server_url: str) -> None:
        """Add a server to the pool."""
        if server_url in self._server_health:
            if not self._server_health[server_url]:
                self._server_health[server_url] = True
                if server_url not in self._healthy_servers:
                    self._healthy_servers.append(server_url)
        else:
            self._server_health[server_url] = True
            self._healthy_servers.append(server_url)

    def remove_server(self, server_url: str) -> None:
        """Remove a server from the pool entirely."""
        if server_url in self._server_health:
            self._server_health.pop(server_url, None)
        with contextlib.suppress(ValueError):
            self._healthy_servers.remove(server_url)

    def get_all_servers(self) -> List[str]:
        """Get all known servers (healthy and unhealthy)."""
        return list(self._server_health.keys())

    def get_healthy_servers(self) -> List[str]:
        """Get current healthy servers."""
        return list(self._healthy_servers)

    def is_healthy(self, server_url: str) -> Optional[bool]:
        """Return health status for a server, or None if unknown."""
        return self._server_health.get(server_url)

    async def mark_healthy(self, server_url: str) -> None:
        """Mark a server as healthy and ensure it participates in rotation."""
        async with self._lock:
            if server_url not in self._server_health:
                self._server_health[server_url] = True
            else:
                self._server_health[server_url] = True

            if server_url not in self._healthy_servers:
                self._healthy_servers.append(server_url)

    async def mark_unhealthy(self, server_url: str) -> None:
        """Mark a server as unhealthy and remove it from rotation."""
        async with self._lock:
            if server_url in self._server_health:
                self._server_health[server_url] = False

            with contextlib.suppress(ValueError):
                self._healthy_servers.remove(server_url)

    async def get_healthy_server_snapshot(self) -> List[str]:
        """Return a snapshot of currently healthy servers."""
        async with self._lock:
            return list(self._healthy_servers)

    async def get_server_health_snapshot(self) -> Dict[str, bool]:
        """Return a snapshot of all server health states."""
        async with self._lock:
            return dict(self._server_health)

    def __len__(self) -> int:
        """Return the number of healthy servers in the pool."""
        return len(self._healthy_servers)
