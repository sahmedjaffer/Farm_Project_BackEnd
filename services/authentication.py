# services/authentication.py
from zoneinfo import ZoneInfo
from fastapi import Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from models.user import User, user_pydanticIn, user_pydantic
from auth import create_access_token, verify_password, get_password_hash


class OAuth2PasswordRequestFormCustom:
    def __init__(
        self,
        username: str = Form(..., description="User email"),
        password: str = Form(..., description="User password"),
    ):
        self.username = username
        self.password = password
        self.grant_type = "password"
        self.scopes = []
        self.client_id = None
        self.client_secret = None

# ===== Login =====
async def login_service(form_data: OAuth2PasswordRequestFormCustom = Depends()):
    user = await User.get_or_none(email=form_data.username)
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials"
        )

    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": await user_pydantic.from_tortoise_orm(user)
    }

# ===== Register =====
userIn=user_pydanticIn
async def register_service(user_info: userIn):
    existing_user = await User.get_or_none(email=user_info.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash the password before saving
    hashed_password = get_password_hash(user_info.password)
    user_obj = await User.create(
        first_name=user_info.first_name,
        last_name=user_info.last_name,
        email=user_info.email,
        password=hashed_password,
        # last_login=None 
    )

    return {
        "status": "Ok",
        "data": await user_pydantic.from_tortoise_orm(user_obj)
    }
