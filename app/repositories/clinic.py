from app.db.models.clinic import Clinic
from app.repositories.base import BaseRepository


class ClinicRepository(BaseRepository[Clinic]):
    def __init__(self):
        super().__init__(Clinic)

    # additional clinic-specific queries
    async def get_by_domain(self, db, domain: str):
        result = await db.execute(
            select(self.model).where(self.model.domain == domain)
        )
        return result.scalar_one_or_none()
