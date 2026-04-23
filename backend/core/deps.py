from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.exceptions import ForbiddenError, UnauthorizedError
from core.security import decode_token
from models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise UnauthorizedError()
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id), User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError()
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise ForbiddenError("Admin role required")
    return current_user


async def require_estimator_or_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.admin, UserRole.estimator):
        raise ForbiddenError("Estimator or Admin role required")
    return current_user
