# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# import models
# from database import get_db
# from .schemas import RoleCreate, RolePermissionCreate, RoleResponse, RolePermissionResponse
# from .crud import create_role, create_role_permission
#
# router = APIRouter(prefix="/roles")
#
#
# @router.post("/", response_model=RoleResponse)
# async def create_role_endpoint(role: RoleCreate, db: AsyncSession = Depends(get_db)):
#
#     existing_role = await db.execute(
#         select(models.Role).where(models.Role.name == role.name)
#     )
#     if existing_role.scalars().first():
#         raise HTTPException(400, "Role already exists")
#
#     # Use the CRUD function
#     return await create_role(db, role)
#
#
# @router.post("/permissions/", response_model=RolePermissionResponse)
# async def create_role_permission_endpoint(permission: RolePermissionCreate, db: AsyncSession = Depends(get_db)):
#     # Validate role exists
#     role = await db.get(models.Role, permission.role_id)
#     if not role:
#         raise HTTPException(400, "Role does not exist")
#
#     # Check duplicate permission
#     existing = await db.execute(
#         select(models.RolePermission).where(
#             models.RolePermission.role_id == permission.role_id,
#             models.RolePermission.permission == permission.permission
#         )
#     )
#     if existing.scalars().first():
#         raise HTTPException(400, "Permission already exists for this role")
#
#     # Use the CRUD function
#     return await create_role_permission(db, permission)