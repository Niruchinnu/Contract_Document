import pdfplumber
import docx
import pytesseract
from PIL import Image
import os
import csv
from fastapi import UploadFile,File, HTTPException


pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"  # Windows path example

async def extract_text_from_image(file_path: str) -> str:
    image = Image.open(file_path)
    text = pytesseract.image_to_string(image)
    return text.strip()

async def extract_text_from_docx(file_path: str) -> str:
    doc = docx.Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.strip()

async def extract_text_from_pdf_with_ocr(file_path: str) -> str:
    with pdfplumber.open(file_path) as pdf:
        text = ""
        for page in pdf.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                text += extracted_text + "\n"
            else:
                image = page.to_image(resolution=300)
                pil_image = image.annotated
                text += pytesseract.image_to_string(pil_image) + "\n"
    return text.strip()

async def extract_text_from_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()
    return text.strip()

async def extract_text_from_csv(file_path: str) -> str:
    text = ""
    with open(file_path, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        text = "\n".join([", ".join(row) for row in reader])
    return text.strip()

async def extract_text(file: UploadFile=File(...)):
    file_extension = file.filename.split(".")[-1].lower()
    temp_file_path = f"temp_uploaded_file.{file_extension}"

    with open(temp_file_path, "wb") as buffer:
        buffer.write(file.file.read())

    extracted_text = ""
    if file_extension == "docx":
        extracted_text = await extract_text_from_docx(temp_file_path)
    elif file_extension in ["jpg","jpeg","png"]:
        extracted_text = await extract_text_from_image(temp_file_path)
    elif file_extension == "pdf":
        extracted_text = await extract_text_from_pdf_with_ocr(temp_file_path)
    elif file_extension == "txt":
        extracted_text = await extract_text_from_txt(temp_file_path)
    elif file_extension == "csv":
        extracted_text = await extract_text_from_csv(temp_file_path)
    else:
        os.remove(temp_file_path)
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF, DOCX, TXT, JPG, CSV or PNG.")
    os.remove(temp_file_path)
    return extracted_text

