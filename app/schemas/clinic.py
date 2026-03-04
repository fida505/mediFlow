from pydantic import BaseModel
from datetime import datetime


class ClinicBase(BaseModel):
    name: str
    domain: str


class ClinicCreate(ClinicBase):
    pass


class ClinicRead(ClinicBase):
    id: int
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
