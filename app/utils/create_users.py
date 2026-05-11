import sys
import string
import secrets
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import delete
from app.config import get_settings
from sqlalchemy.orm import sessionmaker
from app.models.user import User, UserRole
from app.services.auth import hash_password
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession


def generate_secure_password(length: int = 16) -> str:
    """Generate a secure, random alphanumeric password with special characters."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def reset_and_create_users():
    """Deletes all users, creates two default users, and saves credentials to a file."""
    settings = get_settings()

    # Create async engine and session
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    users_to_create = [
        {"email": "development@spctek.com", "username": "Development"},
        {"email": "marketing@spctek.com", "username": "Marketing"},
    ]

    async with async_session() as session:
        try:
            print("\n=== Resetting Users Table ===")

            # 1. Delete all existing users
            print("Deleting existing users...")
            await session.execute(delete(User))

            # 2. Generate credentials and create new users
            creds_data = []
            for user_info in users_to_create:
                password = generate_secure_password()
                hashed_pw = hash_password(password)

                new_user = User(
                    email=user_info["email"],
                    username=user_info["username"],
                    hashed_password=hashed_pw,
                    user_role=UserRole.ADMIN,
                )
                session.add(new_user)

                # Keep track of the raw credentials for the text file
                creds_data.append((user_info["email"], password))

            # 3. Commit transactions
            await session.commit()
            print("✓ New users successfully committed to the database.")

            # 4. Write credentials to creds.txt in CWD
            creds_file_path = Path.cwd() / "creds.txt"
            with open(creds_file_path, "w", encoding="utf-8") as f:
                f.write("=== GENERATED CREDENTIALS ===\n\n")
                for email, password in creds_data:
                    f.write(f"Email: {email}\n")
                    f.write(f"Password: {password}\n")
                    f.write("-" * 30 + "\n")

            print(f"✓ Credentials successfully saved to: {creds_file_path}\n")

        except Exception as e:
            print(f"\n✗ Error during execution: {str(e)}\n")
            await session.rollback()
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reset_and_create_users())
