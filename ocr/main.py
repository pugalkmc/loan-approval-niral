# Installed Libraries
import uvicorn
import logging
import torch
import aiofiles
from PIL import Image
from pathlib import Path
from fastapi import FastAPI, HTTPException, File, UploadFile
from .extract import extract_text_from_image, load_model_once

# Internal Libraries
from config.settings import IS_CUDA_CHECK_NEEDED, CUDA_CONFIGURED

load_model_once()

# Python Libraries
import os
import time

if CUDA_CONFIGURED=='1':
    torch.cuda.empty_cache()
    torch.cuda.ipc_collect()

if IS_CUDA_CHECK_NEEDED == '1':
    if torch.cuda.is_available():
        logger.info("GPU Available")
    else:
        logger.error("GPU not accessible, stopping program")
        exit()

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the base directory from an environment variable, with a default value
BASE_DIR = Path(os.getenv("OCR_BASE_DIR", "/home/sumith/Downloads/server/ocr"))

@app.post("/extract-text")
async def process_data(file: UploadFile = File(...)) -> dict:
    file_path = None
    try:
        # Validate if the file is an image
        file.file.seek(0)  # Reset file pointer
        try:
            image = Image.open(file.file)
            image.verify()  # Verify image integrity
            file.file.seek(0)  # Reset again for further operations
        except Exception as e:
            logger.error(f"Uploaded file is not a valid image: {e}")
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")
        
        # Create the /image directory if it doesn't exist
        image_dir = BASE_DIR / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate a unique file name using timestamp
        timestamp = int(time.time())
        file_path = image_dir / f"{timestamp}_{file.filename}"
        
        async with aiofiles.open(file_path, "wb") as buffer:
            await buffer.write(await file.read())
            buffer.write(await file.read())
        
        # Call the extract_text_from_image function with the saved file path
        result = extract_text_from_image(str(file_path))
        
        # Return the result
        logger.info(f"Extracted text: {result['extracted_text']}")
        return result
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("An error occurred while processing the file.")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
    
    finally:
        # Delete the image file after use if it was saved
        if file_path and file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Deleted image file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete image file {file_path}: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)