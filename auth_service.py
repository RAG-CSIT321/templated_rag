import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends
from chat_history_mysql import ChatHistoryMySQL
import os
from typing import Optional

# Secret key for JWT - in production use a proper secret from environment variables
SECRET_KEY = os.getenv("JWT_SECRET", "baohanxinhvailon14032004")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 100

class AuthService:
    def __init__(self):
        self.db = ChatHistoryMySQL()
    
    def hash_password(self, password: str) -> str:
        """Hash a password for storing."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except:
            return False
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def register_user(self, username: str, password: str, email: Optional[str] = None):
        """Register a new user"""
        cursor = self.db.connection.cursor()
        
        # Check if username exists
        cursor.execute("SELECT 1 FROM user_auth WHERE username = %s", (username,))
        if cursor.fetchone():
            cursor.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email exists
        if email:
            cursor.execute("SELECT 1 FROM user_auth WHERE email = %s", (email,))
            if cursor.fetchone():
                cursor.close()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Create user
        user_id = f"user_{int(datetime.now().timestamp())}"
        password_hash = self.hash_password(password)
        created_at = datetime.now()
        
        try:
            # Create user in users table
            self.db.create_user_if_not_exists(user_id, username)
            
            # Create auth record
            cursor.execute(
                """INSERT INTO user_auth 
                (user_id, username, email, password_hash, created_at) 
                VALUES (%s, %s, %s, %s, %s)""",
                (user_id, username, email, password_hash, created_at)
            )
            
            self.db.connection.commit()
            return {"status": "success", "user_id": user_id}
        except Exception as e:
            self.db.connection.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
        finally:
            cursor.close()
    
    def authenticate_user(self, username: str, password: str):
        """Authenticate a user and return JWT token if successful"""
        cursor = self.db.connection.cursor(dictionary=True)
        
        cursor.execute(
            "SELECT user_id, username, password_hash FROM user_auth WHERE username = %s",
            (username,)
        )
        user = cursor.fetchone()
        cursor.close()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Username does not exist",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not self.verify_password(password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = self.create_access_token(
            data={"sub": user['username'], "user_id": user['user_id']},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user['user_id']
        }
    
    def get_current_user(self, token: str):
        """Get current user from JWT token"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            user_id: str = payload.get("user_id")
            if username is None or user_id is None:
                raise credentials_exception
        except jwt.PyJWTError:
            raise credentials_exception
        
        return {"username": username, "user_id": user_id}
    
    def check_username_exists(self, username: str) -> bool:
        """Check if a username already exists in the database"""
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT 1 FROM user_auth WHERE username = %s", (username,))
        exists = cursor.fetchone() is not None
        cursor.close()
        return exists

