from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from app.database.connection import users_collection
from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Fetch user from MongoDB (user_id is a manually chosen string, not an ObjectId)
    user = await users_collection.find_one({"_id": user_id})
    if user is None:
        raise credentials_exception

    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is disabled")

    return user

def require_roles(*allowed_roles: str):
    """
    Dependency factory: use as Depends(require_roles("admin")) or
    Depends(require_roles("admin", "doctor")) to restrict a route to
    specific roles. Raises 403 for anyone else.
    """
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of these roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker