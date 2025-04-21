# Installed Libraries
import aiofiles
import httpx
import logging
import shutil
from fastapi import File, UploadFile, HTTPException
from pdf2image import convert_from_path
from torchvision import transforms
import cv2

# Internal Libraries
from config import OCR_SERVER_IP, LLM_SERVER_IP

# Python Libraries
import time
import os
from datetime import datetime
import concurrent.futures

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Function to remove watermark from an image using thresholding
def remove_watermark(image_path):
    # Read the image
    img = cv2.imread(image_path, 1)

    # Apply a threshold to remove the watermark
    img1 = cv2.imread(image_path)
    _, thresh = cv2.threshold(img1, 150, 255, cv2.THRESH_BINARY)

    # Generate a timestamp for the output file name
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    output_path = f"gate_score_without_watermark_{timestamp}.jpg"

    # Save the image after thresholding (watermark removed)
    cv2.imwrite(output_path, thresh)
    return output_path


poppler_path = r"C:\Program Files\Release-24.08.0-0\poppler-24.08.0\Library\bin"
IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

def clear_images_directory():
    if os.path.exists(IMAGES_DIR):
        shutil.rmtree(IMAGES_DIR)
    os.makedirs(IMAGES_DIR)

clear_images_directory()

async def save_file(file: UploadFile, extension: str) -> str:
    file_path = os.path.join(IMAGES_DIR, f"uploaded_{int(time.time())}.{extension}")
    file.file.seek(0)
    
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(await file.read())
    
    logger.info(f"File saved at {file_path}")
    return file_path

async def save_image_file(file: UploadFile, document_type: str) -> str:
    allowed_formats = {"image/png": "png", "image/jpeg": "jpg"}
    extension = allowed_formats.get(file.content_type)
    if not extension:
        logger.error(f"Unsupported image format: {file.content_type}")
        raise HTTPException(status_code=400, detail="Unsupported image format")
    
    normal_path = await save_file(file, extension)
    return normal_path

async def extract_text_from_image(image_path: str, document_type) -> str:
    if document_type == "gate_score":
        return remove_watermark(image_path)
    async with aiofiles.open(image_path, "rb") as f:
        image_data = await f.read()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"http://{OCR_SERVER_IP}:8001/extract-text",
                files={"file": (os.path.basename(image_path), image_data, "image/png")}
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"API Error: {e.response.text}")
            raise HTTPException(status_code=500, detail="Text extraction API failed")
        except Exception as e:
            logger.error(f"HTTP request error: {e}")
            raise HTTPException(status_code=500, detail="Unable to connect to text extraction API")

        return response.json()

async def convert_pdf_to_images(pdf_path: str) -> list:
    images = convert_from_path(pdf_path, dpi=200)
    transform = transforms.ToTensor()

    def process_image(i, image):
        image_tensor = transform(image)
        output_image = transforms.ToPILImage()(image_tensor.cpu())
        image_path = os.path.join(IMAGES_DIR, f'page_{i + 1}.png')
        output_image.save(image_path, quality=95)
        return image_path

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process_image, i, image) for i, image in enumerate(images)]
        processed_images = [future.result() for future in concurrent.futures.as_completed(futures)]

    return processed_images

async def process_pdf_file(file: UploadFile = File(...), schema: str = None, document_type: str = None):

    processed_images = []
    image_path = None
    try:
        if file.content_type == "application/pdf":
            pdf_path = await save_file(file, "pdf")
            processed_images = await convert_pdf_to_images(pdf_path)

            extracted_texts = []
            for image_path in processed_images:
                text = await extract_text_from_image(image_path, document_type)
                extracted_texts.append(text['extracted_text'])

            combined_text = "\n\n".join(extracted_texts)

            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(
                        f"http://{LLM_SERVER_IP}:8002/process-data",
                        json={"raw_text": combined_text, "schema": schema}
                    )
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    logger.error(f"API Error: {e.response.text}")
                    raise HTTPException(status_code=500, detail="Data processing API failed")
                except Exception as e:
                    logger.error(f"HTTP request error: {e}")
                    raise HTTPException(status_code=500, detail="Unable to connect to data processing API")

                return response.json()

        elif file.content_type.startswith("image/"):
            image_path = await save_image_file(file, document_type)
            text = await extract_text_from_image(image_path, document_type)
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(
                        f"http://{LLM_SERVER_IP}:8002/process-data",
                        json={"raw_text": text['extracted_text'], "schema": schema}
                    )
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    logger.error(f"API Error: {e.response.text}")
                    raise HTTPException(status_code=500, detail="Data processing API failed")
                except Exception as e:
                    logger.error(f"HTTP request error: {e}")
                    raise HTTPException(status_code=500, detail="Unable to connect to data processing API")
                
                return response.json()

        else:
            logger.error("Invalid file format")
            raise HTTPException(status_code=400, detail="Invalid file format. Only PDF or image files are allowed.")
    finally:
        if file.content_type == "application/pdf" and processed_images:
            for image_path in processed_images:
                if os.path.exists(image_path):
                    os.remove(image_path)
            os.remove(pdf_path)
        elif file.content_type.startswith("image/") and image_path:
            if os.path.exists(image_path):
                os.remove(image_path)