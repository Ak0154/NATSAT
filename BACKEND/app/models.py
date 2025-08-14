# app/models.py

from typing import Optional
from datetime import datetime

from beanie import Document
from pydantic import BaseModel, Field, EmailStr # <-- Add this import

class User(Document):
    name: str
    email: EmailStr
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"

