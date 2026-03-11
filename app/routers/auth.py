from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
async def login(data: LoginRequest):
    if data.email == "drbuddies2@gmail.com" and data.password == "Drbuddies@3639":
        return {"token": "secure-session-789", "message": "Login successful"}
    
    raise HTTPException(status_code=401, detail="Invalid email or password")
