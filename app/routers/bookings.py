from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from datetime import datetime

router = APIRouter()

class SettingsUpdate(BaseModel):
    daily_limit: int

class BookingCreate(BaseModel):
    patient_name: str
    patient_phone: str
    slot_id: int
    date: str
    notes: str = None

class BookingUpdate(BaseModel):
    patient_name: str = None
    patient_phone: str = None
    slot_id: int = None
    date: str = None
    notes: str = None

async def init_db(db: AsyncSession):
    """Initializes tables and migrations in a single block for better startup speed."""
    try:
        # 1. Create tables
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS dashboard_bookings (
                id TEXT PRIMARY KEY,
                patient_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                notes TEXT,
                time TEXT NOT NULL,
                date TEXT NOT NULL DEFAULT '',
                slot_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS dashboard_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS dashboard_daily_limit (
                date TEXT PRIMARY KEY,
                limit_value INTEGER NOT NULL
            );
        """))
        
        # 2. Seed default daily limit
        res = await db.execute(text("SELECT 1 FROM dashboard_settings WHERE key = 'daily_limit'"))
        if not res.fetchone():
            await db.execute(text("INSERT INTO dashboard_settings (key, value) VALUES ('daily_limit', '45')"))

        # 3. Migrations (Check and Add columns)
        # We use a safer approach for migrations in production
        res = await db.execute(text("SELECT * FROM dashboard_bookings LIMIT 0"))
        cols = res.keys()
        
        if 'date' not in cols:
            await db.execute(text("ALTER TABLE dashboard_bookings ADD COLUMN date TEXT NOT NULL DEFAULT ''"))
        if 'slot_id' not in cols:
            await db.execute(text("ALTER TABLE dashboard_bookings ADD COLUMN slot_id INTEGER"))
            
        # 4. Indexes for performance
        await db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bookings_date ON dashboard_bookings(date);
            CREATE INDEX IF NOT EXISTS idx_bookings_slot ON dashboard_bookings(slot_id);
        """))
        
        await db.commit()
    except Exception as e:
        print(f"!!! DB INIT/MIGRATION ERROR: {e}")
        await db.rollback()

async def get_daily_limit(db: AsyncSession) -> int:
    res = await db.execute(text("SELECT value FROM dashboard_settings WHERE key = 'daily_limit'"))
    row = res.mappings().first()
    return int(row['value']) if row else 45

async def get_capacity_for_date(db: AsyncSession, date_str: str) -> int:
    # Check for specific override first
    res = await db.execute(text("SELECT limit_value FROM dashboard_daily_limit WHERE date = :date"), {"date": date_str})
    row = res.mappings().first()
    if row:
        return int(row['limit_value'])
    
    # Fallback to global setting
    return await get_daily_limit(db)

@router.get("")
async def get_bookings(date: str = Query(None), db: AsyncSession = Depends(get_db)):
    try:
        if date:
            result = await db.execute(text("SELECT id, patient_name, phone, notes, time, date, slot_id FROM dashboard_bookings WHERE date = :date"), {"date": date})
        else:
            result = await db.execute(text("SELECT id, patient_name, phone, notes, time, date, slot_id FROM dashboard_bookings"))
        
        # Explicit mapping to avoid any Row vs Mapping issues
        bookings_list = []
        for row in result.mappings().all():
            bookings_list.append({
                "id": row['id'],
                "patient_name": row['patient_name'],
                "patient_phone": row['phone'], # Map 'phone' column to 'patient_phone' for frontend consistency
                "notes": row['notes'],
                "time": row['time'],
                "date": row['date'],
                "slot_id": row['slot_id']
            })
        return bookings_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/settings")
async def get_settings(db: AsyncSession = Depends(get_db)):
    limit = await get_daily_limit(db)
    return {"daily_limit": limit}

@router.post("/settings")
async def update_settings(settings: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("UPDATE dashboard_settings SET value = :val WHERE key = 'daily_limit'"), {"val": str(settings.daily_limit)})
        await db.commit()
        return {"message": "Settings updated", "daily_limit": settings.daily_limit}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/month-stats")
async def get_month_stats(month: str = Query(...), db: AsyncSession = Depends(get_db)):
    """month format: YYYY-MM"""
    import asyncio
    try:
        # Run queries sequentially - AsyncSession does not support concurrent operations on the same session
        global_limit = await get_daily_limit(db)
        
        counts_res = await db.execute(text("""
            SELECT date, COUNT(*) as count 
            FROM dashboard_bookings 
            WHERE date LIKE :pattern
            GROUP BY date
        """), {"pattern": f"{month}-%"})
        counts = {row['date']: row['count'] for row in counts_res.mappings().all()}

        limits_res = await db.execute(text("""
            SELECT date, limit_value 
            FROM dashboard_daily_limit 
            WHERE date LIKE :pattern
        """), {"pattern": f"{month}-%"})
        limits = {row['date']: row['limit_value'] for row in limits_res.mappings().all()}

        return {"limit": global_limit, "counts": counts, "overrides": limits}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/daily-limit")
async def get_daily_limit_route(date: str = Query(...), db: AsyncSession = Depends(get_db)):
    limit = await get_capacity_for_date(db, date)
    return {"date": date, "limit": limit}

class DailyLimitUpdate(BaseModel):
    date: str
    limit: int

@router.post("/daily-limit")
async def update_daily_limit(data: DailyLimitUpdate, db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("""
            INSERT INTO dashboard_daily_limit (date, limit_value) 
            VALUES (:date, :limit)
            ON CONFLICT (date) DO UPDATE SET limit_value = EXCLUDED.limit_value
        """), {"date": data.date, "limit": data.limit})
        await db.commit()
        return {"message": "Daily limit updated", "date": data.date, "limit": data.limit}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics")
async def get_analytics(date: str = Query(None), db: AsyncSession = Depends(get_db)):
    try:
        import asyncio
        from datetime import date as pydate
        
        # Determine "today"
        today = date if date else pydate.today().isoformat()

        # Run queries sequentially to avoid Session concurrency errors
        daily_limit = await get_capacity_for_date(db, today)
        global_limit = await get_daily_limit(db)
        
        today_booked_res = await db.execute(text("SELECT COUNT(*) FROM dashboard_bookings WHERE date = :today"), {"today": today})
        today_booked = today_booked_res.scalar() or 0
        
        total_booked_res = await db.execute(text("SELECT COUNT(*) FROM dashboard_bookings"))
        total_total = total_booked_res.scalar() or 0
        
        trends_res = await db.execute(text("""
            SELECT date, COUNT(*) as count 
            FROM dashboard_bookings 
            GROUP BY date 
            ORDER BY date DESC 
            LIMIT 30
        """))
        daily_data = [dict(row) for row in trends_res.mappings().all()]
        
        today_remaining = max(0, daily_limit - today_booked)
        avg = round(total_total / len(daily_data), 1) if daily_data else 0
        
        return {
            "today_date": today,
            "today_booked": today_booked,
            "today_remaining": today_remaining,
            "daily_limit": daily_limit,
            "global_limit": global_limit,
            "total": total_total,
            "average_per_day": avg,
            "daily_trends": daily_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")

@router.post("")
async def create_booking(booking: BookingCreate, db: AsyncSession = Depends(get_db)):
    try:
        # ID includes date and slot to allow same slot on different days
        booking_id = f"appt-{booking.date}-{booking.slot_id}"
        
        result = await db.execute(text("SELECT id FROM dashboard_bookings WHERE id = :id"), {"id": booking_id})
        if result.fetchone():
            raise HTTPException(status_code=400, detail="Slot already booked for this date")
            
        await db.execute(text("""
            INSERT INTO dashboard_bookings (id, patient_name, phone, notes, time, date, slot_id)
            VALUES (:id, :name, :phone, :notes, :time, :date, :slot_id)
        """), {
            "id": booking_id,
            "name": booking.patient_name,
            "phone": booking.patient_phone,
            "notes": booking.notes or "",
            "time": str(booking.slot_id),
            "date": booking.date,
            "slot_id": booking.slot_id
        })
        await db.commit()
        return {"message": "Booking created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create booking: {str(e)}")

@router.put("/{booking_id}")
async def update_booking(booking_id: str, booking: BookingUpdate, db: AsyncSession = Depends(get_db)):
    try:
        # Get current booking
        res = await db.execute(text("SELECT * FROM dashboard_bookings WHERE id = :id"), {"id": booking_id})
        if not res.fetchone():
            raise HTTPException(status_code=404, detail="Booking not found")
            
        # Build update query
        updates = []
        params = {"id": booking_id}
        
        if booking.patient_name is not None:
            updates.append("patient_name = :name")
            params["name"] = booking.patient_name
        if booking.patient_phone is not None:
            updates.append("phone = :phone")
            params["phone"] = booking.patient_phone
        if booking.notes is not None:
            updates.append("notes = :notes")
            params["notes"] = booking.notes
        if booking.slot_id is not None:
            updates.append("slot_id = :slot_id")
            updates.append("time = :time")
            params["slot_id"] = booking.slot_id
            params["time"] = str(booking.slot_id)
        if booking.date is not None:
            updates.append("date = :date")
            params["date"] = booking.date
            
        if not updates:
            return {"message": "No changes made"}
            
        query = f"UPDATE dashboard_bookings SET {', '.join(updates)} WHERE id = :id"
        await db.execute(text(query), params)
        await db.commit()
        return {"message": "Booking updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update: {str(e)}")

@router.delete("/{booking_id}")
async def delete_booking(booking_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("DELETE FROM dashboard_bookings WHERE id = :id"), {"id": booking_id})
        await db.commit()
        return {"message": "Booking deleted successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
