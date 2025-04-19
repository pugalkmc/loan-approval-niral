from dotenv import load_dotenv
import os

# Load environment variables from a .env file
load_dotenv()

# Example: Accessing an environment variable
IS_CUDA_CHECK_NEEDED = os.getenv("IS_CUDA_CHECK_NEEDED")
CUDA_CONFIGURED = os.getenv("CUDA_CONFIGURED")
CUDA_VISIBLE_DEVICES = os.getenv("CUDA_VISIBLE_DEVICES")

MONGO_DB_URL = os.getenv("MONGO_DB_URL")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

SECRET_KEY = os.getenv("SECRET_KEY")

OCR_SERVER_IP = os.getenv("OCR_SERVER_IP")
LLM_SERVER_IP = os.getenv("LLM_SERVER_IP")