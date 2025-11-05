"""
Main entry point for the HTTP Load Balancer.
"""
import asyncio
import logging
import sys
from typing import List

import aiohttp.web

from load_balancer.balancer import create_app
from load_balancer.config import config
from load_balancer.server_pool import ServerPool

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format=config.log_format,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def create_server_pool() -> ServerPool:
    """
    Create and initialize the server pool from configuration.
    
    Returns:
        Initialized ServerPool instance
    """
    servers = config.backend_servers
    logger.info(f"Initializing server pool with {len(servers)} servers:")
    for server in servers:
        logger.info(f"  - {server}")
    
    return ServerPool(servers)


def main():
    """Main entry point for the load balancer application."""
    logger.info("Starting HTTP Load Balancer...")
    logger.info(f"Listening on {config.lb_host}:{config.lb_port}")
    
    # Create server pool
    server_pool = create_server_pool()
    
    if len(server_pool) == 0:
        logger.error("No backend servers configured!")
        sys.exit(1)
    
    # Create web application
    app = create_app(server_pool)
    
    # Start the web server
    try:
        aiohttp.web.run_app(
            app,
            host=config.lb_host,
            port=config.lb_port,
            print=lambda _: None  # Suppress default print
        )
    except KeyboardInterrupt:
        logger.info("Shutting down load balancer...")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

