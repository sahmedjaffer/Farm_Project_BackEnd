from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt, os
from passlib.context import CryptContext
from models.user import User
from dotenv import load_dotenv

# Load environment variables from the .env file
# This must be done before calling os.getenv() to ensure variables are available
load_dotenv()

# Password hashing context using bcrypt
# 'deprecated="auto"' allows Passlib to handle outdated hashes automatically
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme to extract the Bearer token from the Authorization header
# 'tokenUrl' points to the login endpoint where tokens are obtained
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def verify_password(plain_password, hashed_password):
    """
    Compare a plain text password with a hashed password.
    Returns True if they match, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """
    Hash a plain text password using bcrypt.
    """
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token.
    
    Parameters:
        data (dict): The payload data to include in the token (e.g., {"sub": "user@example.com"}).
        expires_delta (timedelta, optional): Custom expiration time. 
            If not provided, default from ACCESS_TOKEN_EXPIRE_MINUTES env variable is used.
    
    Returns:
        str: Encoded JWT token.
    """
    to_encode = data.copy()  # Make a copy so we don't modify the original data
    # Set token expiration time (either provided or default from env variable)
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")))
    to_encode.update({"exp": expire})  # Add expiration claim
    # Encode the token using the secret key and algorithm from environment variables
    return jwt.encode(to_encode, os.getenv("SECRET_KEY"), algorithm=os.getenv("ALGORITHM"))

def decode_access_token(token: str):
    """
    Decode and validate a JWT access token.
    
    Parameters:
        token (str): The JWT token string.
    
    Returns:
        dict: Decoded token payload if valid.
    
    Raises:
        HTTPException: If the token is invalid or expired.
    """
    try:
        return jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
    except jwt.PyJWTError:
        # Any JWT decoding error will raise an HTTP 401 Unauthorized
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Dependency function for FastAPI to retrieve the currently authenticated user.
    
    Parameters:
        token (str): Automatically extracted Bearer token from the request header.
    
    Returns:
        User: The user object from the database.
    
    Raises:
        HTTPException: If the token payload is invalid or the user doesn't exist.
    """
    payload = decode_access_token(token)  # Decode and validate the token
    username: str = payload.get("sub")  # Extract the 'subject' (usually email or username)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    # Look up the user in the database by email
    user = await User.get_or_none(email=username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
