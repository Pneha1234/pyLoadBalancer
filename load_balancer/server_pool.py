"""
Server pool management with round-robin load balancing.
"""
import asyncio
from collections import deque
from typing import List, Optional


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
        # Convert list to deque for efficient rotation
        self.servers = deque(servers)
        # Use asyncio.Lock for thread-safe async operations
        self._lock = asyncio.Lock()
        
    def get_next_server(self) -> Optional[str]:
        """
        Get the next server using round-robin algorithm.
        
        Returns:
            URL of the next server, or None if no servers available
        """
        if not self.servers:
            return None
            
        # Rotate the queue to get next server
        # rotate(-1) moves first element to end (circular rotation)
        server = self.servers[0]
        self.servers.rotate(-1)
        return server
    
    async def get_next_server_async(self) -> Optional[str]:
        """
        Thread-safe async version of get_next_server.
        
        Returns:
            URL of the next server, or None if no servers available
        """
        async with self._lock:
            if not self.servers:
                return None
                
            # Get first server and rotate
            server = self.servers[0]
            self.servers.rotate(-1)
            return server
    
    def add_server(self, server_url: str) -> None:
        """Add a server to the pool."""
        if server_url not in self.servers:
            self.servers.append(server_url)
    
    def remove_server(self, server_url: str) -> None:
        """Remove a server from the pool."""
        if server_url in self.servers:
            self.servers.remove(server_url)
    
    def get_all_servers(self) -> List[str]:
        """Get all servers in the pool."""
        return list(self.servers)
    
    def __len__(self) -> int:
        """Return the number of servers in the pool."""
        return len(self.servers)
