"""
Snowflake ID Generator

Wrapper around the snowflake-id library for generating distributed unique IDs.
Uses Twitter's Snowflake algorithm to generate 64-bit IDs.
"""

from typing import Optional
from snowflake import SnowflakeGenerator

import logging

logger = logging.getLogger(__name__)

# Global ID generator instance
_id_generator: Optional[SnowflakeGenerator] = None


def get_id_generator() -> SnowflakeGenerator:
    """
    Get the global ID generator instance
    
    Returns:
        Snowflake ID generator instance
        
    Raises:
        RuntimeError: If generator is not initialized
    """
    global _id_generator
    
    if _id_generator is None:
        raise RuntimeError(
            "ID generator not initialized. "
            "Call init_id_generator() in application lifespan."
        )
    
    return _id_generator


def generate_id() -> str:
    """
    Generate a unique Snowflake ID as string
    
    Returns:
        Unique ID as string
    """
    generator = get_id_generator()
    return str(next(generator))


def generate_id_int() -> int:
    """
    Generate a unique Snowflake ID as integer
    
    Returns:
        Unique 64-bit integer ID
    """
    generator = get_id_generator()
    return next(generator)


def init_id_generator(instance_id: int = 1) -> None:
    """
    Initialize global Snowflake ID generator
    
    Should be called once during application startup in lifespan.
    
    Args:
        instance_id: Unique instance ID for this service (0-1023)
                    In production, this should be:
                    - Stored in a distributed configuration center (e.g., etcd, Consul)
                    - Automatically assigned when service instances start
                    - Managed by orchestration system (e.g., Kubernetes StatefulSet)
    
    Raises:
        ValueError: If instance_id is out of valid range
    """
    global _id_generator
    
    # Already initialized
    if _id_generator is not None:
        logger.warning("ID generator already initialized, skipping")
        return
    
    # Validate instance_id
    if instance_id < 0 or instance_id > 1023:
        raise ValueError(
            f"Instance ID must be between 0 and 1023, got {instance_id}"
        )
    
    _id_generator = SnowflakeGenerator(instance_id)
    logger.info(f"ID generator initialized with instance_id={instance_id}")


def close_id_generator() -> None:
    """
    Close and cleanup ID generator
    
    Optional cleanup function for application shutdown.
    """
    global _id_generator
    
    if _id_generator is not None:
        logger.info("Closing ID generator...")
        _id_generator = None
        logger.info("ID generator closed")


if __name__ == "__main__":
    # Test ID generation
    print("Testing Snowflake ID Generator")
    print("=" * 50)
    
    # Initialize with instance ID 1
    init_id_generator(instance_id=1)
    
    print("\nGenerating 10 sample IDs:")
    for i in range(10):
        id_str = generate_id()
        print(f"  {i+1:2d}. {id_str}")
    
    print("\nAll IDs generated successfully!")
    
    # Cleanup
    close_id_generator()
