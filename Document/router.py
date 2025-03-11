from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Depends, HTTPException
from .kafka_producer import send_to_kafka
import base64
import logging
import models
import json
from Auth import crud
from database import get_db
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contract_document")

async def process_files_and_send(files, user_id):
    logger.info("⏳ Background task started")

    kafka_message = {
        "user_id": user_id,
        "files": []
    }

    for file in files:
        filename = file.filename
        file_content = await file.read()
        file_content_base64 = base64.b64encode(file_content).decode("utf-8")

        kafka_message["files"].append({
            "filename": filename,
            "file_content": file_content_base64
        })

    logger.info("📨 Sending message to Kafka")
    await send_to_kafka("document-processing", kafka_message)
    logger.info("✅ Message sent to Kafka successfully")


@router.post("/upload/")
async def upload_documents(background_tasks: BackgroundTasks, files: list[UploadFile] = File(...), current_user: models.User = Depends(crud.get_current_user)):
    logger.info("📢 Received API request")

    user_id = current_user.id
    background_tasks.add_task(process_files_and_send, files, user_id)

    logger.info("✅ API returned response immediately")
    return {"message": f"{len(files)} files uploaded. Processing will be handled asynchronously."}

@router.get("/get_revisions")
async def view_database(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(crud.get_current_user)
):
    """
    Endpoint to view all file revisions in the database, restricted by role:
    - superadmin and admin: sees all revisions
    - user: see only their own revisions
    """
    try:
        if current_user.role in ["superadmin", "admin"]:
            stmt = select(models.Revision)
        else:
            stmt = select(models.Revision).where(models.Revision.uploaded_by == current_user.id)

        result = await db.execute(stmt)  # Await execution
        revisions = result.scalars().all()  # Fetch all results

        return {
            "revisions": [
                {
                    "id": rev.id,
                    "filename": rev.filename,
                    "revision": rev.revision,
                    "data": rev.data if isinstance(rev.data, dict) else json.loads(rev.data),
                    "diff": rev.diff if isinstance(rev.diff, dict) else (json.loads(rev.diff) if rev.diff else {}),
                    "uploaded_by": rev.uploaded_by,
                    "created_at": rev.created_at.strftime("%Y-%m-%d %H:%M:%S")
                }
                for rev in revisions
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching database records: {str(e)}")