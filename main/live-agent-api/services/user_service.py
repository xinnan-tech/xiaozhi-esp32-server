from sqlalchemy.ext.asyncio import AsyncSession
from repositories import UserModel, User
from utils.security import hash_password, verify_password, generate_jwt_token
from utils.exceptions import BadRequestException, UnauthorizedException, ConflictException
from utils.ulid import generate_user_id
from schemas.user import UserInfo, LoginResponse
from config import settings


class UserService:
    """User service layer"""
    
    async def register(
        self, 
        db: AsyncSession, 
        username: str, 
        password: str
    ) -> None:
        """Register a new user"""
        # Check if username already exists
        if await User.is_username_taken(db, username):
            raise ConflictException("Username already taken")
        
        # Hash password
        hashed_password = hash_password(password)
        
        # Generate user_id
        user_id = generate_user_id()
        
        # Create user
        await User.create(
            db=db,
            user_id=user_id,
            username=username,
            hashed_password=hashed_password
        )
    
    async def login(
        self, 
        db: AsyncSession, 
        username: str, 
        password: str
    ) -> LoginResponse:
        """User login and return JWT token"""
        # Get user by username
        user = await User.get_by_username(db, username)
        if not user:
            raise UnauthorizedException("Invalid username or password, please check and try again")
        
        # Verify password
        if not verify_password(password, user.password):
            raise UnauthorizedException("Invalid username or password, please check and try again")
        
        # Generate JWT token
        token = generate_jwt_token(user.user_id, user.username)
        
        # Prepare response
        user_info = UserInfo(
            user_id=user.user_id,
            username=user.username,
            created_at=user.created_at
        )
        
        return LoginResponse(
            token=token,
            expire=settings.TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # 7 days in seconds
            user=user_info
        )
    
    async def logout(self, db: AsyncSession, token: str) -> None:
        """
        User logout
        
        Note: With JWT, tokens cannot be invalidated on the server side.
        The token will remain valid until it expires.
        For production, consider implementing a token blacklist with Redis.
        """
        # JWT tokens are stateless and cannot be revoked
        # This is a placeholder for future blacklist implementation
        pass
    
    async def update_password(
        self, 
        db: AsyncSession, 
        user_id: str,
        old_password: str,
        new_password: str
    ) -> None:
        """Update user password"""
        # Get user
        user = await User.get_by_user_id(db, user_id)
        if not user:
            raise UnauthorizedException("User not found")
        
        # Verify old password
        if not verify_password(old_password, user.password):
            raise BadRequestException("Invalid old password")
        
        # Hash new password
        new_hashed_password = hash_password(new_password)
        
        # Update password
        await User.update_password(db, user_id, new_hashed_password)
    
    async def get_user_info(self, db: AsyncSession, user_id: str) -> UserModel:
        # Get user from database
        user = await User.get_by_user_id(db, user_id)
        if not user:
            raise UnauthorizedException("User not found")
        
        return user


user_service = UserService()

