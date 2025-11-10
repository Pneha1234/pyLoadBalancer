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

    # Health check configuration
    health_check_interval: float = 5.0
    health_check_timeout: float = 2.0
    health_check_path: str = "/health"
    health_check_method: str = "GET"
    health_check_expected_status: int = 200
    health_check_healthy_threshold: int = 2
    health_check_unhealthy_threshold: int = 2
    
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
HEALTH_CHECK_INTERVAL = config.health_check_interval
HEALTH_CHECK_TIMEOUT = config.health_check_timeout
HEALTH_CHECK_PATH = config.health_check_path
HEALTH_CHECK_METHOD = config.health_check_method
HEALTH_CHECK_EXPECTED_STATUS = config.health_check_expected_status
HEALTH_CHECK_HEALTHY_THRESHOLD = config.health_check_healthy_threshold
HEALTH_CHECK_UNHEALTHY_THRESHOLD = config.health_check_unhealthy_threshold
