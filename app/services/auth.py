import jwt
import bcrypt
from datetime import datetime, timedelta
from app.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode(), hashed_password.encode())


def create_access_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(days=7)

    expire = datetime.utcnow() + expires_delta
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return token


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
