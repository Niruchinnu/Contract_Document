from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import engine, get_db
from .schemas import UserCreate,User,Token,UpdateUser
import models
from .auth import get_password_hash,create_access_token,verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/token")

async def create_user(db: Session, user: UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(username=user.username, email=user.email, hashed_password=hashed_password,role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

async def update_user_in_db(db: Session, user: models.User, user_update: UpdateUser):
    if user_update.username:
        user.username = user_update.username
    if user_update.email:
        user.email = user_update.email
    if user_update.password:
        user.hashed_password = get_password_hash(user_update.password)
    if user_update.role:
        user.role = user_update.role

    db.commit()
    db.refresh(user)
    return user

def check_existing_username(db: Session, username: str):
    db_user = db.query(models.User).filter(models.User.username == username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

# Function to check if email already exists
def check_existing_email(db: Session, email: str):
    db_email = db.query(models.User).filter(models.User.email == email).first()
    if db_email:
        raise HTTPException(status_code=400, detail="Email already registered")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials = verify_token(token)
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(models.User).filter(models.User.username == credentials["username"]).first()
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

