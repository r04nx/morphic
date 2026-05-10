"""
Authentication Service for Morphic Platform
Handles JWT token generation, password hashing, and user authentication
"""
import os
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from models.user import User, UserCreate, UserResponse
from models.database import DatabaseManager


class AuthService:
    """Service for authentication operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.secret_key = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
        self.algorithm = 'HS256'
        self.access_token_expire_minutes = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError:
            return None
    
    def register_user(self, user_data: UserCreate) -> UserResponse:
        """Register a new user"""
        # Check if user already exists
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email = %s", (user_data.email,))
        if cursor.fetchone():
            cursor.close()
            raise ValueError("User with this email already exists")
        
        cursor.execute("SELECT id FROM users WHERE username = %s", (user_data.username,))
        if cursor.fetchone():
            cursor.close()
            raise ValueError("Username already taken")
        
        # Hash password and create user
        password_hash = self.hash_password(user_data.password)
        
        cursor.execute(
            """
            INSERT INTO users (email, username, password_hash, full_name, role, created_at, updated_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, email, username, full_name, role, created_at, is_active
            """,
            (
                user_data.email,
                user_data.username,
                password_hash,
                user_data.full_name,
                'user',
                datetime.utcnow(),
                datetime.utcnow(),
                True
            )
        )
        
        user_row = cursor.fetchone()
        conn.commit()
        cursor.close()
        
        return UserResponse(
            id=user_row[0],
            email=user_row[1],
            username=user_row[2],
            full_name=user_row[3],
            role=user_row[4],
            created_at=user_row[5],
            is_active=user_row[6]
        )
    
    def authenticate_user(self, email: str, password: str) -> Optional[UserResponse]:
        """Authenticate user with email and password"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, email, username, password_hash, full_name, role, created_at, is_active FROM users WHERE email = %s",
            (email,)
        )
        user_row = cursor.fetchone()
        cursor.close()
        
        if not user_row:
            return None
        
        user_id, user_email, username, password_hash, full_name, role, created_at, is_active = user_row
        
        if not self.verify_password(password, password_hash):
            return None
        
        if not is_active:
            return None
        
        return UserResponse(
            id=user_id,
            email=user_email,
            username=username,
            full_name=full_name,
            role=role,
            created_at=created_at,
            is_active=is_active
        )
    
    def get_user_by_id(self, user_id: int) -> Optional[UserResponse]:
        """Get user by ID"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, email, username, full_name, role, created_at, is_active FROM users WHERE id = %s",
            (user_id,)
        )
        user_row = cursor.fetchone()
        cursor.close()
        
        if not user_row:
            return None
        
        return UserResponse(
            id=user_row[0],
            email=user_row[1],
            username=user_row[2],
            full_name=user_row[3],
            role=user_row[4],
            created_at=user_row[5],
            is_active=user_row[6]
        )
    
    def initialize_users_table(self):
        """Initialize users table if it doesn't exist"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                role VARCHAR(20) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        conn.commit()
        cursor.close()
