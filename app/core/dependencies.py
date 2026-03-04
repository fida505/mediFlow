from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db


def get_current_clinic(request: Request):
    cid = getattr(request.state, "clinic_id", None)
    if cid is None:
        raise HTTPException(status_code=403, detail="Clinic context missing")
    return cid


def get_db_with_tenant(db: AsyncSession = Depends(get_db), clinic_id: int = Depends(get_current_clinic)):
    # could set session info or execute set_config statement for RLS if using schemas
    return db
