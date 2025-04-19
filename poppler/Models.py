# Installed packages
from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional

# User registration model
class RegisterModel(BaseModel):
    username: str
    password: str

# User login model
class LoginModel(BaseModel):
    username: str
    password: str

# Job posting model
class JobPostModel(BaseModel):
    title: str

class Biodata(BaseModel):
    name: str
    dob: date
    gender: Optional[str]
    marital_status: Optional[str]
    contact: str
    email: EmailStr
    address: Optional[str]
    profile_picture: Optional[bytes]