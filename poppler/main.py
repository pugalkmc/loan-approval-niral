# Installed Libraries
import logging
import uvicorn
import torch
import jwt
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Internal Libraries
from .process_pdf import process_pdf_file
from .mongodb_config import users_collection, jobs_collection, applications_collection
from .Models import RegisterModel, LoginModel, JobPostModel, Biodata
from config.settings import CUDA_CONFIGURED, SECRET_KEY, IS_CUDA_CHECK_NEEDED

# Python Libraries
import datetime

if CUDA_CONFIGURED=='1':
    torch.cuda.empty_cache()
    torch.cuda.ipc_collect()

logger = logging.getLogger("ocr_logger")
logger.setLevel(logging.INFO)

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

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security scheme for HTTPBearer
security = HTTPBearer()

async def get_user_details(credentials, application_id):
    user_id = verify_jwt_token(credentials)
    # Fetch the application data for the given user_id and application_id
    application = applications_collection.find_one(
        {"user_id": user_id, "application_id": application_id},
        {'biodata.profilePicture': 0}
    )
    
    biodata = application.get("biodata", {})
    education = application.get("education", {'degree': [], 'gateDetails': {}})
    return {"biodata": biodata, "education": education}
    
@app.post("/api/application/{application_id}/upload")
async def validate(
    application_id: str,
    file: UploadFile = File(...),
    schema: str = Form(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    document_type = schema
    userDetails = await get_user_details(credentials, application_id)
    biodata = userDetails['biodata']
    education = userDetails['education']
    
    if schema is None or schema not in prompt_schema:
        return JSONResponse(content={"error": "Schema is required"}, status_code=400)
    
    schema = prompt_schema[schema]

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


# Helper function to create a JWT token
def create_jwt_token(user_id: str) -> str:
    expiration = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    payload = {
        "user_id": user_id,
        "exp": expiration,
        "iat": datetime.datetime.now(datetime.timezone.utc)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

# Helper function to verify JWT token
def verify_jwt_token(credentials: HTTPAuthorizationCredentials):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# API: /api/register
@app.post("/api/register")
async def register(user: RegisterModel):
    existing_user = users_collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Save user in the MongoDB collection
    users_collection.insert_one({"username": user.username, "password": user.password})
    return {"message": "Registration successful"}

# API: /api/login
@app.post("/api/login")
async def login(user: LoginModel):
    # Fetch user from MongoDB
    db_user = users_collection.find_one({"username": user.username})
    if not db_user or db_user["password"] != user.password:
        raise HTTPException(status_code=404, detail="Invalid credentials")
    
    # Generate JWT token
    token = create_jwt_token(user.username)
    return {"message": "Login successful", "token": token}

# API: /api/user (Protected route)
@app.get("/api/user")
async def get_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = verify_jwt_token(credentials)
    # Fetch user details from MongoDB
    user = users_collection.find_one({"username": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"user": user}

# API: /api/job/create (Protected route)
@app.post("/api/job/create")
async def create_job_post(job: JobPostModel, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = verify_jwt_token(credentials)
    job_post = {
        "title": job.title,
        "createdAt": datetime.datetime.now(datetime.timezone.utc),
        "updatedAt": datetime.datetime.now(datetime.timezone.utc),
        "createdBy": user_id
    }
    
    # Save job post in the MongoDB collection
    result = jobs_collection.insert_one(job_post)
    
    # Convert the _id (ObjectId) to a string for JSON serialization
    job_post["_id"] = str(result.inserted_id)
    
    return {"message": "Job post created successfully", "job": job_post}

# API: /api/job (Protected route)
@app.get("/api/job")
async def get_job_posts(credentials: HTTPAuthorizationCredentials = Depends(security)):
    verify_jwt_token(credentials)
    # Fetch job posts from MongoDB
    job_posts = list(jobs_collection.find())
    for job in job_posts:
        job["_id"] = str(job["_id"])
    return {"jobs": job_posts}

# API: /api/biodata (Protected route)
@app.post("/api/biodata")
async def submit_biodata(biodata: Biodata, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = verify_jwt_token(credentials)
    
    # Check if biodata already exists for the user
    existing_biodata = users_collection.find_one({"username": user_id, "biodata": {"$exists": True}})
    if existing_biodata:
        raise HTTPException(status_code=400, detail="Biodata already exists")

    # Save the biodata to the user's record
    users_collection.update_one(
        {"username": user_id},
        {"$set": {"biodata": biodata}}
    )

    return {"message": "Biodata submitted successfully"}

# API: /api/application/{application_id}/biodata (Protected route)
@app.get("/api/application/{application_id}/biodata")
async def get_biodata(application_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = verify_jwt_token(credentials)
    
    # Fetch application details from the applications collection for the user and application_id
    application = applications_collection.find_one({"user_id": user_id, "application_id": application_id})
    if not application:
        # If application not found, create a new application
        new_application = {
            "user_id": user_id,
            "application_id": application_id,
            "createdAt": datetime.datetime.now(datetime.timezone.utc),
            "updatedAt": datetime.datetime.now(datetime.timezone.utc)
        }
        result = applications_collection.insert_one(new_application)
        new_application["_id"] = str(result.inserted_id)
        application = new_application
    else:
        application["_id"] = str(application["_id"])
    
    return application.get('biodata', {})

# API: /api/application/{application_id}/biodata (Protected route)
@app.post("/api/application/{application_id}/biodata")
async def save_application_biodata(application_id: str, biodata: dict, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = verify_jwt_token(credentials)

    # Update the application with the new biodata
    applications_collection.update_one(
        {"user_id": user_id, "application_id": application_id},
        {"$set": {"biodata": biodata, "updatedAt": datetime.datetime.now(datetime.timezone.utc)}},
        upsert=True
    )
    
    return {"message": "Application biodata saved successfully"}


@app.get("/api/application/{application_id}/education")
async def get_education_data(application_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Endpoint to retrieve education data for a specific application.
    The route is protected and requires JWT token for authentication.
    """
    user_id = verify_jwt_token(credentials)

    # Fetch the application data for the given user_id and application_id
    application = applications_collection.find_one(
        {"user_id": user_id, "application_id": application_id}
    )

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # if 'education' in application:
    #     print(application.get("education"))
    # Return the education data
    return {"education": application.get("education", {'degree': [], 'gateDetails': {}})}


@app.post("/api/application/{application_id}/education")
async def save_education_data(application_id: str, education: dict, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Endpoint to save education data for a specific application.
    The route is protected and requires JWT token for authentication.
    """
    user_id = verify_jwt_token(credentials)

    # Update the application with the new education data
    result = applications_collection.update_one(
        {"user_id": user_id, "application_id": application_id},
        {"$set": {"education": education, "updatedAt": datetime.datetime.now(datetime.timezone.utc)}},
        upsert=True
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Application not found")

    return {"message": "Application education data saved successfully"}


@app.get("/api/application/{application_id}/details")
async def get_application_details(application_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Endpoint to retrieve both biodata and education details for a specific application.
    The route is protected and requires JWT token for authentication.
    """
    user_id = verify_jwt_token(credentials)
    # Fetch the application data for the given user_id and application_id
    application = applications_collection.find_one(
        {"user_id": user_id, "application_id": application_id}
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Retrieve biodata and education details
    biodata = application.get("biodata", {})
    education = application.get("education", {'degree': [], 'gateDetails': {}})
    return {"biodata": biodata, "education": education}

# Main entry point for running the app
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3001)
