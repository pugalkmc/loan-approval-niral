# Installed Libraries
import uvicorn
import torch
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

# Internal Libraries
from .gemma import extract_entity
from config.settings import IS_CUDA_CHECK_NEEDED

# Python Libraries


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if IS_CUDA_CHECK_NEEDED=='1':
    if torch.cuda.is_available():
        logger.info("GPU Available")
    else:
        logger.error("GPU not accessible, stopping program")
        exit()

app = FastAPI()

request_id = 1

@app.post("/process-data")
async def process_data(request: Request):
    global request_id
    request_id += 1

    try:
        data = await request.json()
        schema = data.get("schema")
        raw_text = data.get("raw_text")

        # Check if schema is a valid JSON
        if not isinstance(schema, dict):
            raise ValueError("Invalid schema format")
        
        logger.info(f"Request received {request_id}")
        result = await extract_entity(schema, raw_text)
        return JSONResponse(content={'result': result})

    except ValueError as e:
        logger.error(f"ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("An error occurred while processing the request.")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)