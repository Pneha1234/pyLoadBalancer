"""
Health checking utilities for backend servers.
"""
import asyncio
import logging
from collections import defaultdict
from typing import Optional

import aiohttp

from load_balancer.server_pool import ServerPool

logger = logging.getLogger(__name__)


class HealthChecker:
    """Periodically probes backend servers and updates their health status."""

    def __init__(
        self,
        server_pool: ServerPool,
        *,
        interval: float,
        timeout: float,
        path: str,
        method: str,
        expected_status: int,
        healthy_threshold: int,
        unhealthy_threshold: int,
    ) -> None:
        self._server_pool = server_pool
        self._interval = interval
        self._timeout = timeout
        self._path = path if path.startswith("/") else f"/{path}"
        self._method = method
        self._expected_status = expected_status
        self._healthy_threshold = max(1, healthy_threshold)
        self._unhealthy_threshold = max(1, unhealthy_threshold)

        self._session: Optional[aiohttp.ClientSession] = None
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._failure_counts = defaultdict(int)
        self._success_counts = defaultdict(int)

    async def start(self) -> None:
        """Start background health checking."""
        if self._task:
            return

        logger.info(
            "Starting health checker: interval=%ss timeout=%ss path=%s",
            self._interval,
            self._timeout,
            self._path,
        )
        self._stop_event.clear()
        timeout = aiohttp.ClientTimeout(total=self._timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)
        self._task = asyncio.create_task(self._run(), name="health-checker")

    async def stop(self) -> None:
        """Stop background health checking and release resources."""
        if not self._task:
            return

        logger.info("Stopping health checker")
        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

        if self._session:
            await self._session.close()
            self._session = None

    async def _run(self) -> None:
        """Main background loop."""
        try:
            while not self._stop_event.is_set():
                await self._check_all_servers()
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=self._interval
                    )
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            logger.debug("Health checker task cancelled")
            raise
        except Exception:
            logger.exception("Health checker encountered an unexpected error")
        finally:
            self._task = None

    async def _check_all_servers(self) -> None:
        """Run health checks for all servers in the pool."""
        status_snapshot = await self._server_pool.get_server_health_snapshot()
        if not status_snapshot:
            return

        for server_url in status_snapshot.keys():
            await self._check_server(server_url)

    async def _check_server(self, server_url: str) -> None:
        """Probe a single backend server and update status counters."""
        is_healthy = await self._probe(server_url)

        if is_healthy:
            self._failure_counts[server_url] = 0
            self._success_counts[server_url] += 1
            if self._success_counts[server_url] >= self._healthy_threshold:
                if not self._server_pool.is_healthy(server_url):
                    logger.info("Server %s recovered; marking healthy", server_url)
                    await self._server_pool.mark_healthy(server_url)
                self._success_counts[server_url] = 0
        else:
            self._success_counts[server_url] = 0
            self._failure_counts[server_url] += 1
            if self._failure_counts[server_url] >= self._unhealthy_threshold:
                if self._server_pool.is_healthy(server_url):
                    logger.warning("Server %s failed health check; marking unhealthy", server_url)
                    await self._server_pool.mark_unhealthy(server_url)
                self._failure_counts[server_url] = 0

    async def _probe(self, server_url: str) -> bool:
        """Perform the actual HTTP health probe."""
        if not self._session:
            logger.debug("Health checker session not ready; skipping probe")
            return False

        health_url = f"{server_url.rstrip('/')}{self._path}"

        try:
            async with self._session.request(self._method, health_url) as response:
                healthy = response.status == self._expected_status
                if not healthy:
                    logger.debug(
                        "Health check failed for %s: status=%s expected=%s",
                        server_url,
                        response.status,
                        self._expected_status,
                    )
                return healthy
        except aiohttp.ClientError as exc:
            logger.debug("Health check client error for %s: %s", server_url, exc)
            return False
        except asyncio.TimeoutError:
            logger.debug("Health check timeout for %s", server_url)
            return False

