from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
import models
from .schemas import UserCreate, User, Token, UpdateUser
from .crud import (
    check_existing_username, get_current_user, get_admin_user,
    create_user, check_existing_email, update_user_in_db
)
from .auth import create_access_token, verify_password

router = APIRouter(prefix="/users")

@router.post("/", response_model=User)
async def create_superadmin(user: UserCreate, db: AsyncSession = Depends(get_db)):
    await check_existing_email(db, user.email)
    return await create_user(db=db, user=user)

@router.post("/token", response_model=Token)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(models.User).filter(models.User.username == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=User)
async def register_user(
    user: UserCreate,
    admin_or_superadmin: models.User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    existing_super_admin = await db.execute(select(models.User).filter(models.User.role == "superadmin"))
    if user.role == "superadmin" and existing_super_admin.scalars().first():
        raise HTTPException(status_code=400, detail="A superadmin already exists")
    if admin_or_superadmin.role == "admin" and user.role != "user":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins can only create users")
    elif admin_or_superadmin.role == "user":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Users are not allowed to create accounts")
    await check_existing_username(db, user.username)
    await check_existing_email(db, user.email)
    return await create_user(db, user)

@router.put("/{user_id}")
async def update_user(
    user_id: int,
    user_update: UpdateUser,
    current_user: models.User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.role == "admin" and user.role in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Admins can only update users")
    if current_user.role == "user":
        raise HTTPException(status_code=403, detail="Users are not allowed to update accounts")
    existing_superadmin = await db.execute(
        select(models.User).filter(models.User.role == "superadmin", models.User.id != user_id)
    )
    if user_update.role == "superadmin" and existing_superadmin.scalars().first():
        raise HTTPException(status_code=400, detail="A superadmin already exists")
    updated_user = await update_user_in_db(db, user, user_update)
    return {
        "message": "User updated successfully",
        "updated_user": {
            "id": updated_user.id,
            "username": updated_user.username,
            "email": updated_user.email,
            "role": updated_user.role,
        }
    }

@router.delete("/{user_id}")
async def delete_user(user_id: int, admin: models.User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin cannot be deleted")
    if admin.role == "superadmin" or (admin.role == "admin" and user.role == "user"):
        await db.delete(user)
        await db.commit()
        return {"message": "User deleted successfully"}
    raise HTTPException(status_code=403, detail="Admins can only delete users, superadmins can delete both admins and users")

@router.get("/me", response_model=User)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.get("/", response_model=list[User])
async def get_all_users(admin: models.User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    if admin.role == "superadmin":
        result = await db.execute(select(models.User))
        return result.scalars().all()
    elif admin.role == "admin":
        result = await db.execute(select(models.User).filter(models.User.role == "user"))
        return result.scalars().all()
    raise HTTPException(status_code=403, detail="Access denied")
