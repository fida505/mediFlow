from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()

class BookingCreate(BaseModel):
    patient_name: str
    phone: str
    notes: str = ""
    time: str

async def init_db(db: AsyncSession):
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS dashboard_bookings (
            id TEXT PRIMARY KEY,
            patient_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            notes TEXT,
            time TEXT NOT NULL
        )
    """))
    await db.commit()

@router.get("/")
async def get_bookings(db: AsyncSession = Depends(get_db)):
    await init_db(db)
    result = await db.execute(text("SELECT * FROM dashboard_bookings"))
    return [dict(row) for row in result.mappings().all()]

@router.post("/")
async def create_booking(booking: BookingCreate, db: AsyncSession = Depends(get_db)):
    await init_db(db)
    booking_id = "appt-" + booking.time.replace(":", "-")
    
    result = await db.execute(text("SELECT id FROM dashboard_bookings WHERE id = :id"), {"id": booking_id})
    if result.fetchone():
        raise HTTPException(status_code=400, detail="Slot already booked")
        
    await db.execute(text("""
        INSERT INTO dashboard_bookings (id, patient_name, phone, notes, time)
        VALUES (:id, :name, :phone, :notes, :time)
    """), {
        "id": booking_id,
        "name": booking.patient_name,
        "phone": booking.phone,
        "notes": booking.notes,
        "time": booking.time
    })
    await db.commit()
    return {"message": "Booking created successfully"}

@router.delete("/{booking_id}")
async def delete_booking(booking_id: str, db: AsyncSession = Depends(get_db)):
    await init_db(db)
    await db.execute(text("DELETE FROM dashboard_bookings WHERE id = :id"), {"id": booking_id})
    await db.commit()
    return {"message": "Booking deleted successfully"}
