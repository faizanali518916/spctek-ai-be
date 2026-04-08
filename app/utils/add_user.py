import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import get_settings
from app.models.user import User, UserRole
from app.services.auth import hash_password


async def add_user():
    """Interactive script to add a new user."""
    settings = get_settings()

    # Create async engine and session
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            print("\n=== Add New User ===\n")

            # Get user input
            email = input("Enter email: ").strip()
            username = input("Enter username: ").strip()
            password = input("Enter password: ").strip()

            # Ask for role
            print("\nUser roles:")
            print("1. BASIC")
            print("2. ADMIN")
            role_choice = input("Select role (1 or 2) [default: 1]: ").strip() or "1"

            user_role = UserRole.ADMIN if role_choice == "2" else UserRole.BASIC

            # Create user
            hashed_password = hash_password(password)
            user = User(
                email=email,
                username=username,
                hashed_password=hashed_password,
                user_role=user_role,
            )

            session.add(user)
            await session.commit()

            print(f"\n✓ User created successfully!")
            print(f"  Email: {email}")
            print(f"  Username: {username}")
            print(f"  Role: {user_role.value}\n")

        except Exception as e:
            print(f"\n✗ Error creating user: {str(e)}\n")
            await session.rollback()
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(add_user())
