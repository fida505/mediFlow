from app.repositories.clinic import ClinicRepository
from app.db.session import AsyncSession
from app.db.models.clinic import Clinic


class ClinicService:
    def __init__(self, repository: ClinicRepository):
        self.repo = repository

    async def create_clinic(self, db: AsyncSession, name: str, domain: str) -> Clinic:
        data = {"name": name, "domain": domain}
        return await self.repo.create(db, data)

    async def get_clinic(self, db: AsyncSession, clinic_id: int) -> Clinic:
        return await self.repo.get(db, clinic_id)
