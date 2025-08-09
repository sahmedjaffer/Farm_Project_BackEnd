# services/authentication.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from models.user import User, user_pydanticIn, user_pydantic
from auth import create_access_token, verify_password, get_password_hash
from datetime import datetime

# ===== Login =====
async def login_service(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await User.get_or_none(email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials"
        )

    # Update last login time
    user.last_login = datetime.utcnow()
    await user.save()

    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": await user_pydantic.from_tortoise_orm(user)
    }

# ===== Register =====
async def register_service(user_info: user_pydanticIn):
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
        hashed_password=hashed_password
    )

    return {
        "status": "Ok",
        "data": await user_pydantic.from_tortoise_orm(user_obj)
    }
