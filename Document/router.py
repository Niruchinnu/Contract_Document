from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session
from database import get_db
from .crud import get_latest_revision, insert_revision, compute_json_diff
import re
import json
import ollama
from .extract_text import extract_text
import models
from Auth import crud

router = APIRouter(prefix="/contract_document")

async def process_text_with_deepseek(text: str) -> dict:
    """Extracts key-value pairs using DeepSeek API and returns a dictionary."""
    prompt = f"""
    Extract all NER key-value pairs from the given text and return them as a JSON object.
    Respond ONLY with a valid JSON object and NO extra text. No explanations, no reasoning.
    Example format:
    {{
        "Key1": "Value1",
        "Key2": "Value2"
    }}
    Text to analyze: {text}
    """
    try:
        response = ollama.chat(
            model="deepseek-r1:7b",
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = response.get("message", {}).get("content", "")
        if not response_text:
            raise ValueError("Empty response received from model")

        match = re.search(r"\{[\s\S]*\}", response_text, re.DOTALL)
        if not match:
            raise ValueError(f"Invalid JSON structure in response: {response_text}")
        json_str = match.group(0)  # Extract JSON part
        """ Remove trailing commas or other invalid JSON characters """
        json_str = json_str.replace(",}", "}").replace(",]", "]")
        try:
            result = json.loads(json_str)
            return result
        except json.JSONDecodeError as je:
            raise ValueError(f"Failed to parse JSON: {json_str} - Error: {str(je)}")

    except Exception as e:
        print("Error in process_text_with_deepseek:", e)
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@router.post("/upload/")
async def upload_document(file: UploadFile, db: Session = Depends(get_db), current_user: models.User = Depends(crud.get_current_user)):
    filename = file.filename
    text = await extract_text(file)
    user_id = current_user.id
    key_value_pairs = await process_text_with_deepseek(text)
    latest_revision = get_latest_revision(db, filename)
    diff_data = compute_json_diff(latest_revision.data, key_value_pairs) if latest_revision else {}
    new_revision = latest_revision.revision + 1 if latest_revision else 1
    insert_revision(db, filename, new_revision, key_value_pairs, diff_data, user_id)

    return {
        "message": f"File '{filename}' saved as Revision {new_revision}",
        "extracted_data": key_value_pairs,
        "diff": diff_data
    }

@router.get("/get_revisions")
async def view_database(db: Session = Depends(get_db), current_user: models.User = Depends(crud.get_current_user)):
    """
       Endpoint to view all file revisions in the database, restricted by role:
       - superadmin and admin: sees all revisions
       - user: see only their own revisions
       """
    try:
        if current_user.role in ["superadmin", "admin"]:
            revisions = db.query(models.Revision).all()
        else:
            revisions = db.query(models.Revision).filter(models.Revision.uploaded_by == current_user.id).all()
        return {
            "revisions": [
                {
                    "id": rev.id,
                    "filename": rev.filename,
                    "revision": rev.revision,
                    "data": rev.data if isinstance(rev.data, dict) else json.loads(rev.data),
                    "diff": rev.diff if isinstance(rev.diff, dict) else (json.loads(rev.diff) if rev.diff else {}),
                    "uploaded_by": rev.uploaded_by,  # Displaying user_id
                    "created_at": rev.created_at.strftime("%Y-%m-%d %H:%M:%S")  # Formatting timestamp
                }
                for rev in revisions
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching database records: {str(e)}")