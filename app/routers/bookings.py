from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from datetime import datetime

router = APIRouter()

class BookingCreate(BaseModel):
    patient_name: str
    phone: str
    notes: str = ""
    time: str
    date: str  # Format: YYYY-MM-DD

async def init_db(db: AsyncSession):
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS dashboard_bookings (
            id TEXT PRIMARY KEY,
            patient_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            notes TEXT,
            time TEXT NOT NULL,
            date TEXT NOT NULL DEFAULT ''
        )
    """))
    # Check if date column exists (for migration)
    try:
        result = await db.execute(text("PRAGMA table_info(dashboard_bookings)"))
        cols = [row[1] for row in result.all()]
        if 'date' not in cols:
             try:
                await db.execute(text("ALTER TABLE dashboard_bookings ADD COLUMN date TEXT NOT NULL DEFAULT ''"))
             except:
                pass
    except:
        # PRAGMA fails on Postgres. Just try to add column and ignore if exists.
        try:
            await db.execute(text("ALTER TABLE dashboard_bookings ADD COLUMN date TEXT NOT NULL DEFAULT ''"))
        except:
            pass
    await db.commit()

@router.get("")
async def get_bookings(date: str = Query(None), db: AsyncSession = Depends(get_db)):
    await init_db(db)
    if date:
        result = await db.execute(text("SELECT * FROM dashboard_bookings WHERE date = :date"), {"date": date})
    else:
        result = await db.execute(text("SELECT * FROM dashboard_bookings"))
    return [dict(row) for row in result.mappings().all()]

@router.get("/analytics")
async def get_analytics(db: AsyncSession = Depends(get_db)):
    await init_db(db)
    DAILY_LIMIT = 45

    # Get today's date
    from datetime import date
    today = date.today().isoformat()

    # Get today's bookings count
    today_res = await db.execute(text("SELECT COUNT(*) FROM dashboard_bookings WHERE date = :today"), {"today": today})
    today_booked = today_res.fetchone()[0]
    today_remaining = DAILY_LIMIT - today_booked

    # Get total bookings (all time)
    total_res = await db.execute(text("SELECT COUNT(*) as count FROM dashboard_bookings"))
    total = total_res.fetchone()[0]
    
    # Get daily counts for the last 30 days
    daily_res = await db.execute(text("""
        SELECT date, COUNT(*) as count 
        FROM dashboard_bookings 
        GROUP BY date 
        ORDER BY date DESC 
        LIMIT 30
    """))
    daily_data = [dict(row) for row in daily_res.mappings().all()]
    
    # Calculate avg
    avg = total / len(daily_data) if daily_data else 0
    
    return {
        "total": total,
        "average_per_day": round(avg, 1),
        "today_booked": today_booked,
        "today_remaining": today_remaining,
        "daily_limit": DAILY_LIMIT,
        "daily_trends": daily_data
    }

@router.post("")
async def create_booking(booking: BookingCreate, db: AsyncSession = Depends(get_db)):
    await init_db(db)
    # ID includes date to allow same time on different days
    booking_id = f"appt-{booking.date}-{booking.time.replace(':', '-')}"
    
    result = await db.execute(text("SELECT id FROM dashboard_bookings WHERE id = :id"), {"id": booking_id})
    if result.fetchone():
        raise HTTPException(status_code=400, detail="Slot already booked for this date")
        
    await db.execute(text("""
        INSERT INTO dashboard_bookings (id, patient_name, phone, notes, time, date)
        VALUES (:id, :name, :phone, :notes, :time, :date)
    """), {
        "id": booking_id,
        "name": booking.patient_name,
        "phone": booking.phone,
        "notes": booking.notes,
        "time": booking.time,
        "date": booking.date
    })
    await db.commit()
    return {"message": "Booking created successfully"}

@router.delete("/{booking_id}")
async def delete_booking(booking_id: str, db: AsyncSession = Depends(get_db)):
    await init_db(db)
    await db.execute(text("DELETE FROM dashboard_bookings WHERE id = :id"), {"id": booking_id})
    await db.commit()
    return {"message": "Booking deleted successfully"}
