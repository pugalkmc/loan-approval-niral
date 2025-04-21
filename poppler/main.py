# Installed Libraries
import uvicorn
import torch
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Internal Libraries
from .process_pdf import process_pdf_file, logger
from config.settings import CUDA_CONFIGURED, IS_CUDA_CHECK_NEEDED

# Python Libraries

if CUDA_CONFIGURED=='1':
    torch.cuda.empty_cache()
    torch.cuda.ipc_collect()

if IS_CUDA_CHECK_NEEDED == '1':
    if torch.cuda.is_available():
        logger.info("GPU Available")
    else:
        logger.error("GPU not accessible, stopping program")
        exit()

# Initialize the FastAPI application
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

prompt_schema = {
    "aadhaar": {
        "name": "String",
        "aadhaar_number": "Integer, format: 12 digit number",
        "date_of_birth": "String format: DD-MM-YYYY",
        "address": "String",
        "gender": "Male|Female|Other"
    },
    "birth_cert": {
        "name": "String",
        "date_of_birth": "Date, format: DD-MM-YYYY",
        "father_name": "String",
        "mother_name": "String"
    },
    "marksheet": {
        "name": "String",
        "date_of_birth": "Date, Format: DD-MM-YYYY",
        "father_name": "String",
        "mother_name": "String",
        "roll_number": "Integer"
    },
    "degree_cert": {
        "name": "String",
        "university": "String",
        "date_of_birth": "Date Format (DD-MM-YYYY)",
        "degree": "String",
        "cgpa": "Float",
        "percentage": "Float",
        "class": "String",
        "qualification_degree": "String"
    },
    "proof_of_class": {
        "name": "String",
        "class": "String"
    },
    "provisional_cert": {
        "name": "String",
        "degree": "String",
        "university": "String",
        "passing_year": "Integer",
        "qualification_degree": "String"
    },
    "experience_cert": {
        "from_date": "String Format(YYYY-MM-DD)",
        "to_date": "String Format(YYYY-MM-DD)"
    },
    "gate_score_card": {
        "name": "String",
        "registration_number": "String, Mixed of string and Number",
        "year": "Integer(YYYY), Year of the GATE examination",
        "marks_out_of_100": "Float, 0.0 to 100.0",
        "all_india_rank_in_this_paper": "Integer",
        "gate_score": "Integer, 0 to 1000"
    },
    "proof_of_category": {
        "name": "String",
        "category": "String"
    },
    "proof_of_address": {
        "name": "String",
        "address": "String"
    },
    "phd_cert": {
        "name": "String",
        "university": "String",
        "Date_of_reg": "String (YYYY-MM-DD)",
        "title_of_project": "String",
        "no_of_papers_published": "Integer",
        "no_of_conference_attended": "Integer"
    }
}

# Security scheme for HTTPBearer
security = HTTPBearer()
    
@app.post("/validate")
async def validate(
    file: UploadFile = File(...)
):
    document_type = "aadhaar"
    schema = prompt_schema[document_type]

    result = await process_pdf_file(file, schema, document_type)
    try:
        result = eval(result['result'])
    except Exception as e:
        logger.error(f"Error evaluating result: {e}")
        return JSONResponse(content={"error": "Error processing the file"}, status_code=500)
    
    print("LLM Result: ", result)
    if result[0] != document_type:
        return JSONResponse(content={"error": f"Document type mismatch, please provide {document_type} in this section."}, status_code=400)
    
    index = 1
    messages = []
    is_all_valid = True
    for key in schema.keys():
        value = result[index]
        messages.append({'key': key, 'value': value})
        # Assuming validation logic here, update is_all_valid accordingly
        # For demonstration, let's assume any empty value is invalid
        if not value:
            is_all_valid = False
        index += 1

    if is_all_valid:
        return JSONResponse(content={"message": "Document is valid", "messages": messages}, status_code=200)
    else:
        return JSONResponse(content={"messages": messages, "entity": result}, status_code=200)


# Main entry point for running the app
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
