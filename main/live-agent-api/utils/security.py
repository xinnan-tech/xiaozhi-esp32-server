import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

from config import settings


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def generate_jwt_token(user_id: str, username: str) -> str:
    """
    Generate JWT token for authentication
    
    Args:
        user_id: User's unique identifier
        username: User's username
    
    Returns:
        JWT token string
    """
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': now + timedelta(days=settings.TOKEN_EXPIRE_DAYS),
        'iat': now
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def verify_jwt_token(token: str) -> Optional[dict]:
    """
    Verify JWT token and return payload
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload dict if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        # Token has expired
        return None
    except jwt.InvalidTokenError:
        # Token is invalid (tampered, malformed, etc.)
        return None

