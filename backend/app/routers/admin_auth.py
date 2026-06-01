from fastapi import Depends, HTTPException, status

from app.models.user import User
from app.routers.users import get_current_user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not (user.is_admin and user.is_active):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
