from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.clinic_service import ClinicService
from app.repositories.clinic import ClinicRepository
from app.db.session import get_db
from app.schemas.clinic import ClinicCreate, ClinicRead

router = APIRouter()

service = ClinicService(ClinicRepository())

@router.post("", response_model=ClinicRead)
async def create_clinic(payload: ClinicCreate, db: AsyncSession = Depends(get_db)):
    # multi-tenancy bypass since onboarding
    clinic = await service.create_clinic(db, payload.name, payload.domain)
    return clinic

# more endpoints...
