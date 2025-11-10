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
from load_balancer.utils.health_checker import HealthChecker

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
        healthy_servers = await self.server_pool.get_healthy_server_snapshot()
        if not healthy_servers:
            logger.error("No backend servers available")
            return web.Response(
                status=503,
                text="Service Unavailable: No backend servers available"
            )
        
        last_error: Optional[Exception] = None
        body_cache: Optional[bytes] = None

        for _ in range(len(healthy_servers)):
            backend_url = await self.server_pool.get_next_server_async()
            if not backend_url:
                break

            logger.info(
                "Forwarding %s %s to %s", request.method, request.path_qs, backend_url
            )

            # Build target URL
            target_url = f"{backend_url}{request.path_qs}"

            try:
                start_time = time.time()

                if body_cache is None and request.can_read_body:
                    body_cache = await request.read()

                request_data = {
                    "method": request.method,
                    "url": target_url,
                    "headers": dict(request.headers),
                    "allow_redirects": False,
                }

                if body_cache is not None:
                    request_data["data"] = body_cache

                async with self.client_session.request(**request_data) as response:
                    backend_body = await response.read()
                    latency = time.time() - start_time
                    logger.info(
                        "Response from %s: %s (latency: %.3fs)",
                        backend_url,
                        response.status,
                        latency,
                    )
                    return web.Response(
                        status=response.status,
                        headers=dict(response.headers),
                        body=backend_body,
                    )

            except ClientConnectorError as exc:
                last_error = exc
                logger.error("Connection error to %s: %s", backend_url, exc)
                await self.server_pool.mark_unhealthy(backend_url)
                continue
            except ClientTimeout as exc:
                last_error = exc
                logger.error("Request timeout to %s", backend_url)
                await self.server_pool.mark_unhealthy(backend_url)
                continue
            except ClientError as exc:
                last_error = exc
                logger.error("Client error for %s: %s", backend_url, exc)
                await self.server_pool.mark_unhealthy(backend_url)
                continue
            except Exception as exc:
                last_error = exc
                logger.exception("Unexpected error forwarding request via %s", backend_url)
                await self.server_pool.mark_unhealthy(backend_url)
                continue

        return self._build_error_response(last_error)
    
    async def handle_request(self, request: web.Request) -> web.Response:
        """
        Main request handler for all routes.
        
        Args:
            request: Incoming HTTP request
            
        Returns:
            HTTP response
        """
        return await self.forward_request(request)

    def _build_error_response(self, error: Optional[Exception]) -> web.Response:
        """Map transport errors to appropriate HTTP responses."""
        if isinstance(error, ClientTimeout):
            status = 504
            message = "Gateway Timeout: Backend server did not respond in time"
        elif isinstance(error, ClientConnectorError):
            status = 502
            message = "Bad Gateway: Cannot connect to backend server"
        elif isinstance(error, ClientError):
            status = 502
            message = "Bad Gateway: Error communicating with backend server"
        elif error is None:
            status = 503
            message = "Service Unavailable: No backend servers available"
        else:
            status = 500
            message = "Internal Server Error"

        return web.Response(status=status, text=message)


def create_app(
    server_pool: ServerPool,
    *,
    health_checker: Optional[HealthChecker] = None,
) -> web.Application:
    """
    Create and configure the aiohttp web application.
    
    Args:
        server_pool: ServerPool instance
        
    Returns:
        Configured web.Application instance
    """
    app = web.Application()

    balancer = LoadBalancer(server_pool)

    async def on_startup(_: web.Application) -> None:
        await balancer.setup()
        if health_checker:
            await health_checker.start()

    async def on_cleanup(_: web.Application) -> None:
        if health_checker:
            await health_checker.stop()
        await balancer.cleanup()

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    app.router.add_route("*", "/{path:.*}", balancer.handle_request)

    return app

