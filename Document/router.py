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
from .schemas import UpdateExtractedData

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
async def upload_documents(background_tasks: BackgroundTasks, files: list[UploadFile] = File(...)):
    logger.info("📢 Received API request")

    user_id = 1
    background_tasks.add_task(process_files_and_send, files, user_id)

    logger.info("✅ API returned response immediately")
    return {"message": f"{len(files)} files uploaded. Processing will be handled asynchronously."}


@router.get("/get_all_revisions")
async def get_all_revisions(db: AsyncSession = Depends(get_db)):
    """
    Get ALL revision records from database
    Returns: List of all revisions in their raw form
    """
    result = await db.execute(select(models.Revision))
    revisions = result.scalars().all()

    return {
        "revisions": [
            {
                "id": rev.id,
                "filename": rev.filename,
                "revision": rev.revision,
                "data": rev.data,
                "diff": rev.diff,
                "uploaded_by": rev.uploaded_by,
                "created_at": rev.created_at.isoformat() if rev.created_at else None
            }
            for rev in revisions
        ]
    }

@router.put("/update_revision/{revision_id}")
async def update_revision(revision_id: int, update_data: UpdateExtractedData,
                          db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(models.Revision).filter(models.Revision.id == revision_id))
        revision = result.scalars().first()

        if not revision:
            raise HTTPException(status_code=404, detail="Revision not found")
        revision.data = update_data.data
        db.add(revision)
        await db.commit()
        return {
            "message": "Extracted data updated successfully",
            "revision": {
                "extracted_data": revision.data if isinstance(revision.data, dict) else json.loads(revision.data),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating extracted data: {str(e)}")

@router.get("/get_revision/{revision_id}")
async def get_revision(revision_id: int,db: AsyncSession = Depends(get_db),):
    try:
        result = await db.execute(select(models.Revision).filter(models.Revision.id == revision_id))
        revision = result.scalars().first()

        if not revision:
            raise HTTPException(status_code=404, detail="Revision not found")
        return {
            "extracted_data": revision.data if isinstance(revision.data, dict) else json.loads(revision.data),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching extracted data: {str(e)}")


@router.get("/get_revision_by_confidence/{revision_id}")
async def get_revision_by_confidence(revision_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(models.Revision).filter(models.Revision.id == revision_id))
        revision = result.scalars().first()
        if not revision:
            raise HTTPException(status_code=404, detail="Revision not found")
        try:
            extracted_data = revision.data if isinstance(revision.data, dict) else json.loads(revision.data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Invalid JSON format in revision data")
        filtered_data = {
            key: value for key, value in extracted_data.items()
            if isinstance(value, dict) and value.get("confidence", 100) < 70
        }
        if not filtered_data:
            raise HTTPException(status_code=404, detail="No data with confidence score less than 70")

        return {"extracted_data": filtered_data}

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching extracted data: {str(e)}")