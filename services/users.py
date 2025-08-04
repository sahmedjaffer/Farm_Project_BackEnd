from fastapi import Depends, HTTPException
from models.user import User, user_pydantic, user_pydanticIn
from auth import get_current_user


userIn = user_pydanticIn
user = user_pydantic

async def get_all_users_service(current_user: User = Depends(get_current_user)):
    get_all_users_res = await user.from_queryset(User.all())
    if not get_all_users_res:
        raise HTTPException(status_code=404, detail="No users found")
    return {"status": "Ok", "data": get_all_users_res}

async def get_user_by_id_service(user_id: int, current_user: User = Depends(get_current_user)):
    get_user_by_id_res = await user.from_queryset_single(User.get(id=user_id))
    if not get_user_by_id_res:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "Ok", "data": get_user_by_id_res}

async def update_user_service(user_id: int, update_info: userIn, current_user: User = Depends(get_current_user)):
    get_update_user = await User.get(id=user_id)
    update_info = update_info.model_dump(exclude_unset=True)
    
    if "first_name" in update_info:
        get_update_user.first_name = update_info["first_name"]    
    if "last_name" in update_info:
        get_update_user.last_name = update_info["last_name"]
    if "email" in update_info:
        get_update_user.email = update_info["email"]

    await get_update_user.save()
    update_user_res = await user.from_tortoise_orm(get_update_user)
    return {"status": "Ok", "data": update_user_res}

async def delete_user_service(user_id: int, current_user: User = Depends(get_current_user)):
    delete_user_res = await User.get(id=user_id).delete()
    return {"status": "Ok", "data": delete_user_res}