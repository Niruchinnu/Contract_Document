from fastapi import APIRouter, UploadFile
from .kafka_producer import send_to_kafka
import base64


router = APIRouter(prefix="/contract_document")

@router.post("/upload/")
async def upload_document(file: UploadFile):
    filename = file.filename
    user_id = 1
    file_content = await file.read()
    file_content_base64 = base64.b64encode(file_content).decode("utf-8")
    kafka_message = {
        "filename": filename,
        "file_content": file_content_base64,  # Send Base64-encoded content
        "user_id": user_id
    }
    await send_to_kafka("document-processing", kafka_message)
    return {"message": f"File '{filename}' uploaded. Processing will be handled asynchronously."}
# @router.get("/get_revisions")
# async def view_database(db: Session = Depends(get_db), current_user: models.User = Depends(crud.get_current_user)):
#     """
#        Endpoint to view all file revisions in the database, restricted by role:
#        - superadmin and admin: sees all revisions
#        - user: see only their own revisions
#        """
#     try:
#         if current_user.role in ["superadmin", "admin"]:
#             revisions = db.query(models.Revision).all()
#         else:
#             revisions = db.query(models.Revision).filter(models.Revision.uploaded_by == current_user.id).all()
#         return {
#             "revisions": [
#                 {
#                     "id": rev.id,
#                     "filename": rev.filename,
#                     "revision": rev.revision,
#                     "data": rev.data if isinstance(rev.data, dict) else json.loads(rev.data),
#                     "diff": rev.diff if isinstance(rev.diff, dict) else (json.loads(rev.diff) if rev.diff else {}),
#                     "uploaded_by": rev.uploaded_by,  # Displaying user_id
#                     "created_at": rev.created_at.strftime("%Y-%m-%d %H:%M:%S")  # Formatting timestamp
#                 }
#                 for rev in revisions
#             ]
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error fetching database records: {str(e)}")