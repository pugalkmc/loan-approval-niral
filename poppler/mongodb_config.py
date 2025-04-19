# Installed Libraries
from pymongo import MongoClient

# Python Libraries
from config.settings import MONGO_DB_URL, MONGO_DB_NAME

# Initialize MongoDB Client
client = MongoClient(MONGO_DB_URL)

# Access Database
db = client[MONGO_DB_NAME]

# Access Collections
users_collection = db["user"]
admins_collection = db["admins"]
applications_collection = db["applications"]
jobs_collection = db["jobs"]
error_logs_collection = db["error_logs"]