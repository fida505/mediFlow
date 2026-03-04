from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

router = APIRouter()

@router.get("/clinic/{clinic_id}/analytics")
async def analytics(clinic_id: int, db: AsyncSession = Depends(get_db)):
    # compute with queries or Redis cache
    return {"users": 0}
