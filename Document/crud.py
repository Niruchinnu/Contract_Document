from sqlalchemy.orm import Session
from models import Revision


def get_latest_revision(db: Session, filename: str):
    """Fetch the latest revision record instead of just data"""
    return (
        db.query(Revision)
        .filter(Revision.filename == filename)
        .order_by(Revision.revision.desc())
        .first()
    )

def insert_revision(db: Session, filename: str, revision: int, data: dict, diff: dict = None, uploaded_by: int = None):
    """Insert a new revision entry in the database"""
    new_revision = Revision(filename=filename, revision=revision, data=data, diff=diff, uploaded_by=uploaded_by)
    db.add(new_revision)
    db.commit()
    db.refresh(new_revision)
    return new_revision

def compute_json_diff(old_data: dict, new_data: dict) -> dict:
    """Compute differences between two JSON objects"""
    diff = {}
    # Compare new keys/values with old data
    for key, new_val in new_data.items():
        if key not in old_data:
            diff[key] = {"old": None, "new": new_val}
        elif str(old_data[key]) != str(new_val):
            diff[key] = {"old": old_data[key], "new": new_val}
    # Find removed keys
    for key in old_data.keys():
        if key not in new_data:
            diff[key] = {"old": old_data[key], "new": None}
    return diff


