"""
Data models for the application
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class User(BaseModel):
    username: str
    password: str
    date: str = "date"
    firstname: str
    lastname: str
    email: str
    disorder: str = "Not-Diagnosed"
    severity: str = "Not-Diagnosed"
    history: str = ""

class Doctor(BaseModel):
    username: str
    password: str
    firstname: str
    lastname: str
    fees: str
    qualification: str

class LoginRequest(BaseModel):
    username: str
    password: str

class SignupRequest(BaseModel):
    firstname: str
    lastname: str
    username: str
    email: str
    password: str

class DiagnosisRequest(BaseModel):
    user_input: str
    step: int = 1

class CounselingRequest(BaseModel):
    user_input: str
    session_id: str = "default"

class DiagnosisResponse(BaseModel):
    message: str
    disorder: Optional[str] = None
    severity: Optional[str] = None
    completed: bool = False

class CounselingResponse(BaseModel):
    message: str
    session_id: str
