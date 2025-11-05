"""
Configuration module for the HTTP Load Balancer.
"""
from dataclasses import dataclass
from typing import List


@dataclass
class Config:
    """Configuration class for the load balancer."""
    
    # Load balancer settings
    lb_host: str = "0.0.0.0"
    lb_port: int = 8080
    
    # Backend servers pool
    backend_servers: List[str] = None
    
    # Timeout settings (in seconds)
    request_timeout: int = 30
    connect_timeout: int = 5
    
    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    def __post_init__(self):
        """Initialize default backend servers if not provided."""
        if self.backend_servers is None:
            self.backend_servers = [
                "http://localhost:9001",
                "http://localhost:9002",
                "http://localhost:9003",
            ]


# Create a global config instance
config = Config()

# For backward compatibility, you can also access as module-level constants
LB_HOST = config.lb_host
LB_PORT = config.lb_port
BACKEND_SERVERS = config.backend_servers
REQUEST_TIMEOUT = config.request_timeout
CONNECT_TIMEOUT = config.connect_timeout
LOG_LEVEL = config.log_level
LOG_FORMAT = config.log_format
