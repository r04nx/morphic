"""
User Model for Morphic Platform
Handles user data structure and validation
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    """User data model"""
    id: Optional[int] = None
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password_hash: str
    full_name: Optional[str] = None
    role: str = "user"  # user, admin
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


class UserCreate(BaseModel):
    """User creation schema"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login schema"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response schema (without password)"""
    id: int
    email: str
    username: str
    full_name: Optional[str]
    role: str
    created_at: datetime
    is_active: bool


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
