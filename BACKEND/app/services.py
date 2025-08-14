# app/services.py

from typing import Optional
from passlib.context import CryptContext

from app.models import User
from app.schemas import UserCreate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hashes a plain text password."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a hashed password."""
    return pwd_context.context.verify(plain_password, hashed_password)

async def get_user_by_email(email: str) -> Optional[User]:
    """Finds a user in the database by their email address."""
    return await User.find_one(User.email == email)

async def create_user(user_data: UserCreate) -> User:
    """Creates a new user and inserts them into the database."""
    hashed_password = get_password_hash(user_data.password)
    user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hashed_password
    )
    return await user.insert()