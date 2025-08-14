#!/usr/bin/env python3
"""
Redis configuration for browser-use Railway deployment.
Handles Redis connection for session caching and queue management.
"""

import os
import redis
import aioredis
from typing import Optional, Dict, Any
from urllib.parse import urlparse

def get_redis_config() -> Optional[Dict[str, Any]]:
    """Get Redis configuration from environment variables."""
    
    # Option 1: Full Redis URL (preferred)
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        parsed = urlparse(redis_url)
        return {
            'host': parsed.hostname,
            'port': parsed.port or 6379,
            'password': parsed.password,
            'db': int(parsed.path[1:]) if parsed.path and len(parsed.path) > 1 else 0,
            'decode_responses': True
        }
    
    # Option 2: Individual Redis parameters
    redis_host = os.getenv('REDIS_HOST')
    if redis_host:
        return {
            'host': redis_host,
            'port': int(os.getenv('REDIS_PORT', 6379)),
            'password': os.getenv('REDIS_PASSWORD'),
            'db': int(os.getenv('REDIS_DB', 0)),
            'decode_responses': True
        }
    
    return None

def get_redis_client() -> Optional[redis.Redis]:
    """Get synchronous Redis client."""
    config = get_redis_config()
    if not config:
        return None
    
    try:
        client = redis.Redis(**config)
        # Test connection
        client.ping()
        return client
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")
        return None

async def get_async_redis_client() -> Optional[aioredis.Redis]:
    """Get asynchronous Redis client."""
    config = get_redis_config()
    if not config:
        return None
    
    try:
        client = aioredis.from_url(
            f"redis://{config['host']}:{config['port']}/{config['db']}",
            password=config.get('password'),
            decode_responses=True
        )
        # Test connection
        await client.ping()
        return client
    except Exception as e:
        print(f"⚠️  Async Redis connection failed: {e}")
        return None

def is_redis_available() -> bool:
    """Check if Redis is available and configured."""
    return get_redis_config() is not None