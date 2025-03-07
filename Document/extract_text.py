import pdfplumber
import docx
import pytesseract
from PIL import Image
import os
import csv
from fastapi import UploadFile,File, HTTPException
import re
import json
import ollama


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

