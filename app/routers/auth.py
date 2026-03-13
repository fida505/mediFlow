from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

router = APIRouter()

VALID_USERS = [
    {"email": "drbuddies2@gmail.com", "password": "Drbuddies@3639"},
    {"email": "Jmrclinic332@gmail.com", "password": "Jmr@9894CL2"},
]

@router.post("/login")
async def login(data: LoginRequest):
    for user in VALID_USERS:
        if data.email == user["email"] and data.password == user["password"]:
            return {"token": "secure-session-789", "message": "Login successful"}
    
    raise HTTPException(status_code=401, detail="Invalid email or password")
