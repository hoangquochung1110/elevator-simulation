"""
Cache service configuration.

This module provides configuration settings for the cache service,
with support for environment variable overrides.
"""

import os

# Get Redis host and port from environment variables
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

# Default cache settings
DEFAULT_CACHE_SETTINGS = {
    "BACKEND": "redis",
    "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/0",
    "OPTIONS": {
        "socket_timeout": 5.0,
        "socket_connect_timeout": 5.0,
        "socket_keepalive": True,
        "max_connections": 10,
    },
    "KEY_PREFIX": "cache:",
    "TIMEOUT": 300,  # 5 minutes
    "VERSION": 1,
}
