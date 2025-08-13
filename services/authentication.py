# Import necessary modules and functions
from zoneinfo import ZoneInfo
from fastapi import Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from models.user import User, user_pydanticIn, user_pydantic
from config.auth import create_access_token, verify_password, get_password_hash


# Custom form class to handle login form data using FastAPI's Form dependency
class OAuth2PasswordRequestFormCustom:
    def __init__(
        self,
        username: str = Form(..., description="User email"),  # Email input field
        password: str = Form(..., description="User password"),  # Password input field
    ):
        self.username = username
        self.password = password
        self.grant_type = "password"  # OAuth2 grant type, fixed as "password"
        self.scopes = []  # OAuth2 scopes (empty here)
        self.client_id = None  # Not used in this implementation
        self.client_secret = None  # Not used in this implementation


# ===== Login Service =====
async def login_service(form_data: OAuth2PasswordRequestFormCustom = Depends()):
    """
    Authenticate user by verifying email and password.
    Returns JWT access token and user data if successful.
    """

    # Try to get the user record from database by email (username)
    user = await User.get_or_none(email=form_data.username)

    # If user not found or password doesn't match, raise error
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials"  # Return generic login failure message
        )

    # If credentials are valid, create JWT access token with user's email as subject
    access_token = create_access_token(data={"sub": user.email})

    # Return the token type and token, along with user data serialized by Pydantic
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": await user_pydantic.from_tortoise_orm(user)
    }


# ===== Register Service =====
# Pydantic input model for user registration data
userIn = user_pydanticIn

async def register_service(user_info: userIn):
    """
    Register a new user after checking email uniqueness.
    Password is hashed before saving to the database.
    """

    # Check if email already exists in the database
    existing_user = await User.get_or_none(email=user_info.email)
    if existing_user:
        # If email is already registered, raise an error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash the password securely before saving
    hashed_password = get_password_hash(user_info.password)

    # Create new user record in the database
    user_obj = await User.create(
        first_name=user_info.first_name,
        last_name=user_info.last_name,
        email=user_info.email,
        password=hashed_password,
        # last_login can be added here if you want to track login times
    )

    # Return success status and the created user data serialized by Pydantic
    return {
        "status": "Ok",
        "data": await user_pydantic.from_tortoise_orm(user_obj)
    }
