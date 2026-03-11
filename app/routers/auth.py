from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(data: LoginRequest):
    # For demo purposes, we allow any username and password
    return {"token": "demo-token-123", "message": "Login successful"}
