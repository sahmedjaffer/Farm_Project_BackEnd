from uuid import UUID
from fastapi import Depends, HTTPException
from models.user import User, UserUpdate, user_pydantic, user_pydanticIn
from config.auth import get_current_user, get_password_hash


userIn = user_pydanticIn  # Input Pydantic model for user data validation
user = user_pydantic      # Output Pydantic model for user serialization




# Service to update an existing user by their UUID id
# Requires authenticated current user
async def update_user_service(
    user_id: UUID,
    update_info: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    # Fetch user
    try:
        db_user = await User.get(id=user_id)
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = update_info.dict(exclude_unset=True)  # only fields provided

    for field, value in update_data.items():
        if field == "password":
            db_user.password = get_password_hash(value)
        else:
            setattr(db_user, field, value)

    await db_user.save()
    updated_user_res = await user_pydantic.from_tortoise_orm(db_user)
    return {"status": "Ok", "data": updated_user_res}

# Service to delete a user by UUID id
# Requires authenticated current user
async def delete_user_service(user_id: UUID, current_user: User = Depends(get_current_user)):
    # Delete the user by id from the database
    delete_user_res = await User.get(id=user_id).delete()
    
    # Return success status and result of the delete operation (usually number of deleted rows)
    return {"status": "Ok", "data": delete_user_res}
