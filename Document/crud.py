from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Revision

async def get_latest_revision(db: AsyncSession, filename: str):
    """Fetch the latest revision record using async session"""
    result = await db.execute(
        select(Revision).filter(Revision.filename == filename).order_by(Revision.revision.desc())
    )
    return result.scalars().first()

async def insert_revision(db: AsyncSession, filename: str, revision: int, data: dict, diff: dict = None, uploaded_by: int = None):
    """Insert a new revision entry using async session"""
    new_revision = Revision(filename=filename, revision=revision, data=data, diff=diff, uploaded_by=uploaded_by)
    db.add(new_revision)
    await db.commit()
    await db.refresh(new_revision)
    return new_revision

def compute_json_diff(old_data: dict, new_data: dict) -> dict:
    """Compute differences between two JSON objects (does not need async)"""
    diff = {}
    for key, new_val in new_data.items():
        if key not in old_data:
            diff[key] = {"old": None, "new": new_val}
        elif str(old_data[key]) != str(new_val):
            diff[key] = {"old": old_data[key], "new": new_val}
    for key in old_data.keys():
        if key not in new_data:
            diff[key] = {"old": old_data[key], "new": None}
    return diff