from fastapi import Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends

from utils.security import verify_jwt_token
from utils.exceptions import UnauthorizedException


# Define Bearer token security scheme
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Get current user ID from JWT Bearer token (no database query)
    
    This is the recommended dependency for most APIs that only need user_id.
    It's faster because it doesn't query the database.
    
    Usage:
        Authorization: Bearer <jwt_token>
    
    Flow:
    1. Extract Bearer token from Authorization header
    2. Verify JWT token (signature, expiration)
    3. Extract and return user_id from token payload
    """
    token = credentials.credentials
    
    # Verify JWT token and extract payload
    payload = verify_jwt_token(token)
    if not payload:
        raise UnauthorizedException("Invalid or expired token")
    
    return payload['user_id']

