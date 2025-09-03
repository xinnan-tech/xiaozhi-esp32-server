import redis

# Redis connection configuration
redis_client = redis.Redis(
    host='yamanote.proxy.rlwy.net',
    port=34938,
    password='YbdhwguVUNowduNpDZjuSefZFhBXiOEP',
    username='default',
    db=0,
    decode_responses=True,
    socket_timeout=30,
    socket_connect_timeout=30
)

try:
    print("Connecting to Redis...")
    # Test connection
    redis_client.ping()
    print("Successfully connected to Redis!")
    
    # Get all keys to see what's cached
    keys = redis_client.keys('*')
    print(f"Found {len(keys)} keys in Redis:")
    for key in keys[:10]:  # Show first 10 keys
        print(f"  - {key}")
    
    if len(keys) > 10:
        print(f"  ... and {len(keys) - 10} more keys")
    
    # Clear all data in current database
    result = redis_client.flushdb()
    print(f"Redis cache cleared: {result}")
    
    # Verify it's cleared
    keys_after = redis_client.keys('*')
    print(f"Keys remaining after clear: {len(keys_after)}")
    
except redis.exceptions.ConnectionError as e:
    print(f"Failed to connect to Redis: {e}")
except Exception as e:
    print(f"Error: {e}")