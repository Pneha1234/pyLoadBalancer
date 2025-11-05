"""
Core reverse proxy and load balancing logic.
"""
import logging
import time
from typing import Optional

import aiohttp
from aiohttp import web
from aiohttp.client_exceptions import ClientError, ClientConnectorError, ClientTimeout

from load_balancer.config import config
from load_balancer.server_pool import ServerPool

logger = logging.getLogger(__name__)


class LoadBalancer:
    """
    HTTP Load Balancer that forwards requests to backend servers.
    """
    
    def __init__(self, server_pool: ServerPool):
        """
        Initialize the load balancer.
        
        Args:
            server_pool: ServerPool instance for server selection
        """
        self.server_pool = server_pool
        self.client_session: Optional[aiohttp.ClientSession] = None
        
    async def setup(self):
        """Initialize the HTTP client session."""
        timeout = aiohttp.ClientTimeout(
            total=config.request_timeout,
            connect=config.connect_timeout
        )
        self.client_session = aiohttp.ClientSession(timeout=timeout)
        logger.info("Load balancer client session initialized")
    
    async def cleanup(self):
        """Clean up resources."""
        if self.client_session:
            await self.client_session.close()
            logger.info("Load balancer client session closed")
    
    async def forward_request(self, request: web.Request) -> web.Response:
        """
        Forward incoming request to a backend server.
        
        Args:
            request: Incoming HTTP request from client
            
        Returns:
            HTTP response from backend server or error response
        """
        # Get next server from pool (async-safe)
        backend_url = await self.server_pool.get_next_server_async()
        
        if not backend_url:
            logger.error("No backend servers available")
            return web.Response(
                status=503,
                text="Service Unavailable: No backend servers available"
            )
        
        # Build target URL
        target_url = f"{backend_url}{request.path_qs}"
        
        logger.info(
            f"Forwarding {request.method} {request.path_qs} to {backend_url}"
        )
        
        # Forward request
        try:
            start_time = time.time()
            
            # Prepare request data
            request_data = {
                "method": request.method,
                "url": target_url,
                "headers": dict(request.headers),
                "allow_redirects": False,
            }
            
            # Add body if present (for POST, PUT, PATCH, etc.)
            if request.can_read_body:
                request_data["data"] = await request.read()
            
            # Make request to backend
            async with self.client_session.request(**request_data) as response:
                # Read response body
                body = await response.read()
                
                # Calculate latency
                latency = time.time() - start_time
                logger.info(
                    f"Response from {backend_url}: {response.status} "
                    f"(latency: {latency:.3f}s)"
                )
                
                # Create response with same status and headers
                return web.Response(
                    status=response.status,
                    headers=dict(response.headers),
                    body=body
                )
                
        except ClientConnectorError as e:
            logger.error(f"Connection error to {backend_url}: {e}")
            return web.Response(
                status=502,
                text=f"Bad Gateway: Cannot connect to backend server"
            )
            
        except ClientTimeout:
            logger.error(f"Request timeout to {backend_url}")
            return web.Response(
                status=504,
                text="Gateway Timeout: Backend server did not respond in time"
            )
            
        except ClientError as e:
            logger.error(f"Client error for {backend_url}: {e}")
            return web.Response(
                status=502,
                text=f"Bad Gateway: Error communicating with backend server"
            )
            
        except Exception as e:
            logger.exception(f"Unexpected error forwarding request: {e}")
            return web.Response(
                status=500,
                text="Internal Server Error"
            )
    
    async def handle_request(self, request: web.Request) -> web.Response:
        """
        Main request handler for all routes.
        
        Args:
            request: Incoming HTTP request
            
        Returns:
            HTTP response
        """
        return await self.forward_request(request)


def create_app(server_pool: ServerPool) -> web.Application:
    """
    Create and configure the aiohttp web application.
    
    Args:
        server_pool: ServerPool instance
        
    Returns:
        Configured web.Application instance
    """
    app = web.Application()
    
    # Create load balancer instance
    balancer = LoadBalancer(server_pool)
    
    # Setup and cleanup handlers
    app.on_startup.append(lambda _: balancer.setup())
    app.on_cleanup.append(lambda _: balancer.cleanup())
    
    # Add catch-all route for forwarding all requests
    app.router.add_route('*', '/{path:.*}', balancer.handle_request)
    
    return app

