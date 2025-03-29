from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
from .schemas import UserCreate, UpdateUser
import models
from .auth import get_password_hash, verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/token")


async def create_user(db: AsyncSession = Depends(get_db), user: UserCreate = None):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(username=user.username, email=user.email, hashed_password=hashed_password, role=user.role)

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    return db_user


async def update_user_in_db(db: AsyncSession = Depends(get_db), user: models.User = None,
                            user_update: UpdateUser = None):
    if user_update.username:
        user.username = user_update.username
    if user_update.email:
        user.email = user_update.email
    if user_update.password:
        user.hashed_password = get_password_hash(user_update.password)
    if user_update.role:
        user.role = user_update.role

    await db.commit()
    await db.refresh(user)

    return user


async def check_existing_username(db: AsyncSession, username: str):
    result = await db.execute(select(models.User).filter(models.User.username == username))
    db_user = result.scalar()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")


async def check_existing_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.User).filter(models.User.email == email))
    db_email = result.scalar()
    if db_email:
        raise HTTPException(status_code=400, detail="Email already registered")


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials = verify_token(token)
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(models.User).filter(models.User.username == credentials["username"]))
    user = result.scalar()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


async def get_admin_user(current_user: models.User = Depends(get_current_user)):
    if current_user.role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Only admins and superadmins can perform this action")

    return current_user


async def get_superadmin_user(current_user: models.User = Depends(get_current_user)):
    if current_user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Only superadmins can perform this action")

    return current_user