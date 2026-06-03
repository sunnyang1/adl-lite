"""Authentication service — registration, login, JWT management."""

from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.user import User
from ..schemas.user import TokenResponse, UserCreate, UserRead
from ..utils.jwt_utils import create_access_token, create_refresh_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Handles user registration, login, and JWT token operations."""

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash a plaintext password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def _verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against a bcrypt hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    async def register(db: AsyncSession, user_create: UserCreate) -> UserRead:
        """Register a new user. Raises 409 if email already exists."""
        # Check for duplicate email
        result = await db.execute(select(User).where(User.email == user_create.email))
        existing = result.scalar_one_or_none()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            )

        user = User(
            id=str(uuid4()),
            email=user_create.email,
            hashed_password=AuthService._hash_password(user_create.password),
            full_name=user_create.full_name,
            company=user_create.company,
        )
        db.add(user)
        try:
            await db.flush()
            await db.refresh(user)
        except IntegrityError as err:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            ) from err
        return UserRead.model_validate(user)

    @staticmethod
    async def login(db: AsyncSession, email: str, password: str) -> TokenResponse:
        """Authenticate user and return JWT tokens. Raises 401 on failure."""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None or not AuthService._verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated.",
            )

        access_token = create_access_token(user_id=user.id)
        refresh_token = create_refresh_token(user_id=user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

    @staticmethod
    async def get_current_user(db: AsyncSession, token: str) -> User:
        """Decode JWT and return the corresponding User. Raises 401 if invalid."""
        from ..utils.jwt_utils import decode_token

        payload = decode_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload.",
            )

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated.",
            )
        return user

    @staticmethod
    def refresh_token(refresh_token_str: str) -> TokenResponse:
        """Validate refresh token and issue new access + refresh tokens."""
        from ..utils.jwt_utils import decode_token

        payload = decode_token(refresh_token_str)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            )

        access_token = create_access_token(user_id=user_id)
        new_refresh_token = create_refresh_token(user_id=user_id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )
