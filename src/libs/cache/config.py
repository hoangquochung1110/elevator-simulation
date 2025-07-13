"""
Cache service configuration.

This module provides configuration settings for the cache service,
with support for environment variable overrides.
"""
import os
from typing import Dict, Any, Optional

# Default cache settings
DEFAULT_CACHE_SETTINGS = {
    "BACKEND": "redis",
    "LOCATION": "redis://localhost:6379/0",
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


def get_cache_config(alias: str = "default") -> Dict[str, Any]:
    """Get cache configuration for the given alias.
    
    Args:
        alias: The cache configuration alias to retrieve.
        
    Returns:
        A dictionary containing the cache configuration.
    """
    # In a real application, this would load from a config file or environment
    # For now, we'll just return the default settings with environment overrides
    config = DEFAULT_CACHE_SETTINGS.copy()
    
    # Apply environment variable overrides
    prefix = f"CACHE_{alias.upper()}_"
    
    if os.getenv(f"{prefix}LOCATION"):
        config["LOCATION"] = os.getenv(f"{prefix}LOCATION")
    
    if os.getenv(f"{prefix}BACKEND"):
        config["BACKEND"] = os.getenv(f"{prefix}BACKEND")
    
    if os.getenv(f"{prefix}KEY_PREFIX"):
        config["KEY_PREFIX"] = os.getenv(f"{prefix}KEY_PREFIX")
    
    if os.getenv(f"{prefix}TIMEOUT"):
        try:
            config["TIMEOUT"] = int(os.getenv(f"{prefix}TIMEOUT"))
        except (TypeError, ValueError):
            pass
    
    # Parse options from environment variables
    options = config["OPTIONS"].copy()
    
    for key, value in os.environ.items():
        if key.startswith(f"{prefix}OPTION_"):
            option_name = key[len(f"{prefix}OPTION_"):].lower()
            
            # Try to convert to appropriate type
            if value.isdigit():
                value = int(value)
            elif value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            elif value.replace('.', '', 1).isdigit() and value.count('.') < 2:
                try:
                    value = float(value)
                except ValueError:
                    pass
            
            options[option_name] = value
    
    config["OPTIONS"] = options
    
    return config


def get_redis_params(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Extract Redis connection parameters from a cache config.
    
    Args:
        config: Cache configuration dictionary. If None, uses default config.
        
    Returns:
        Dictionary of Redis connection parameters.
    """
    if config is None:
        config = get_cache_config()
    
    location = config.get("LOCATION", "")
    options = config.get("OPTIONS", {})
    
    # Parse connection string if it's in URL format (redis://...)
    if location.startswith(('redis://', 'rediss://', 'unix://')):
        import redis
        return {
            **redis.connection.parse_url(location),
            **options
        }
    
    # Fall back to individual parameters
    params = {
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "password": None,
    }
    
    if ':' in location:
        host, port = location.split(':', 1)
        params["host"] = host
        try:
            params["port"] = int(port)
        except ValueError:
            pass
    
    # Apply any overrides from options
    for key in ('host', 'port', 'db', 'password', 'socket_timeout', 
               'socket_connect_timeout', 'socket_keepalive', 'max_connections'):
        if key in options:
            params[key] = options[key]
    
    return params
