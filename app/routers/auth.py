from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserLogin, TokenResponse, UserRead
from app.services.auth import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Login with email and password."""
    # Query user by email
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create JWT token
    access_token = create_access_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserRead.model_validate(user),
    )
