from uuid import UUID
from fastapi import Depends, HTTPException
from models.user import User, user_pydantic, user_pydanticIn
from config.auth import get_current_user


userIn = user_pydanticIn  # Input Pydantic model for user data validation
user = user_pydantic      # Output Pydantic model for user serialization


# Service to get all users in the database
# Requires the current user to be authenticated (via Depends on get_current_user)
async def get_all_users_service(current_user: User = Depends(get_current_user)):
    # Query all users and serialize them using Pydantic model
    get_all_users_res = await user.from_queryset(User.all())
    
    # If no users found, raise 404 HTTP error
    if not get_all_users_res:
        raise HTTPException(status_code=404, detail="No users found")
    
    # Return success status and data with all users
    return {"status": "Ok", "data": get_all_users_res}


# Service to get a single user by their UUID id
# Requires authentication of current user
async def get_user_by_id_service(user_id: UUID, current_user: User = Depends(get_current_user)):
    # Query a single user by id and serialize it
    get_user_by_id_res = await user.from_queryset_single(User.get(id=user_id))
    
    # If no user found, raise 404 HTTP error
    if not get_user_by_id_res:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Return success status and user data
    return {"status": "Ok", "data": get_user_by_id_res}


# Service to update an existing user by their UUID id
# Requires authenticated current user
async def update_user_service(user_id: UUID, update_info: userIn, current_user: User = Depends(get_current_user)):
    # Fetch the user object from database by id
    get_update_user = await User.get(id=user_id)
    
    # Convert the incoming Pydantic model to dict excluding unset (missing) fields
    update_info = update_info.model_dump(exclude_unset=True)
    
    # Update the user's fields only if they are present in update_info
    if "first_name" in update_info:
        get_update_user.first_name = update_info["first_name"]
    if "last_name" in update_info:
        get_update_user.last_name = update_info["last_name"]
    if "email" in update_info:
        get_update_user.email = update_info["email"]
    
    # Save changes to the database
    await get_update_user.save()
    
    # Serialize the updated user object to return
    update_user_res = await user.from_tortoise_orm(get_update_user)
    
    # Return success status and updated user data
    return {"status": "Ok", "data": update_user_res}


# Service to delete a user by UUID id
# Requires authenticated current user
async def delete_user_service(user_id: UUID, current_user: User = Depends(get_current_user)):
    # Delete the user by id from the database
    delete_user_res = await User.get(id=user_id).delete()
    
    # Return success status and result of the delete operation (usually number of deleted rows)
    return {"status": "Ok", "data": delete_user_res}
