from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from datetime import datetime

router = APIRouter()

class SettingsUpdate(BaseModel):
    doctor_limits: dict[str, int]

class BookingCreate(BaseModel):
    patient_name: str
    patient_phone: str
    slot_id: int
    date: str
    doctor_id: str = "dr_1"
    notes: str = None
    is_paid: bool = False

class BookingUpdate(BaseModel):
    patient_name: str = None
    patient_phone: str = None
    slot_id: int = None
    date: str = None
    doctor_id: str = None
    notes: str = None
    is_paid: bool = None

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
                slot_id INTEGER,
                doctor_id TEXT NOT NULL DEFAULT 'dr_1',
                is_paid BOOLEAN NOT NULL DEFAULT FALSE
            );
        """))
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS dashboard_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """))
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS dashboard_daily_limit (
                date TEXT NOT NULL,
                doctor_id TEXT NOT NULL DEFAULT 'dr_1',
                limit_value INTEGER NOT NULL,
                PRIMARY KEY (date, doctor_id)
            );
        """))
        
        # 2. Seed default daily limits
        for doc_id in ['dr_1', 'dr_2', 'review']:
            key = f'daily_limit_{doc_id}'
            res = await db.execute(text("SELECT 1 FROM dashboard_settings WHERE key = :key"), {"key": key})
            if not res.fetchone():
                await db.execute(text("INSERT INTO dashboard_settings (key, value) VALUES (:key, '45')"), {"key": key})

        # 3. Migrations (Check and Add columns)
        # We use a safer approach for migrations in production
        res = await db.execute(text("SELECT * FROM dashboard_bookings LIMIT 0"))
        cols = res.keys()
        
        if 'date' not in cols:
            await db.execute(text("ALTER TABLE dashboard_bookings ADD COLUMN date TEXT NOT NULL DEFAULT ''"))
        if 'slot_id' not in cols:
            await db.execute(text("ALTER TABLE dashboard_bookings ADD COLUMN slot_id INTEGER"))
        if 'doctor_id' not in cols:
            await db.execute(text("ALTER TABLE dashboard_bookings ADD COLUMN doctor_id TEXT NOT NULL DEFAULT 'dr_1'"))
        if 'is_paid' not in cols:
            await db.execute(text("ALTER TABLE dashboard_bookings ADD COLUMN is_paid BOOLEAN NOT NULL DEFAULT FALSE"))

        # Migration for dashboard_daily_limit to add doctor_id if missing
        res = await db.execute(text("SELECT * FROM dashboard_daily_limit LIMIT 0"))
        limit_cols = res.keys()
        if 'doctor_id' not in limit_cols:
            # This is a bit tricky since doctor_id is now part of PK. 
            # If migrating from old table without doctor_id:
            await db.execute(text("ALTER TABLE dashboard_daily_limit RENAME TO dashboard_daily_limit_old"))
            await db.execute(text("""
                CREATE TABLE dashboard_daily_limit (
                    date TEXT NOT NULL,
                    doctor_id TEXT NOT NULL DEFAULT 'dr_1',
                    limit_value INTEGER NOT NULL,
                    PRIMARY KEY (date, doctor_id)
                )
            """))
            await db.execute(text("INSERT INTO dashboard_daily_limit (date, doctor_id, limit_value) SELECT date, 'dr_1', limit_value FROM dashboard_daily_limit_old"))
            await db.execute(text("DROP TABLE dashboard_daily_limit_old"))
            
        # 4. Indexes for performance
        await db.execute(text("CREATE INDEX IF NOT EXISTS idx_bookings_date ON dashboard_bookings(date);"))
        await db.execute(text("CREATE INDEX IF NOT EXISTS idx_bookings_slot ON dashboard_bookings(slot_id);"))
        await db.execute(text("CREATE INDEX IF NOT EXISTS idx_bookings_doctor ON dashboard_bookings(doctor_id);"))
        await db.execute(text("CREATE INDEX IF NOT EXISTS idx_daily_limit_date ON dashboard_daily_limit(date);"))
        
        await db.commit()
    except Exception as e:
        print(f"!!! DB INIT/MIGRATION ERROR: {e}")
        await db.rollback()

async def get_daily_limit(db: AsyncSession, doctor_id: str = 'dr_1') -> int:
    key = f'daily_limit_{doctor_id}'
    res = await db.execute(text("SELECT value FROM dashboard_settings WHERE key = :key"), {"key": key})
    row = res.mappings().first()
    return int(row['value']) if row else 45

async def get_capacity_for_date(db: AsyncSession, date_str: str, doctor_id: str = 'dr_1') -> int:
    # Check for specific override first
    res = await db.execute(text("SELECT limit_value FROM dashboard_daily_limit WHERE date = :date AND doctor_id = :doctor_id"), 
                           {"date": date_str, "doctor_id": doctor_id})
    row = res.mappings().first()
    if row:
        return int(row['limit_value'])
    
    # Fallback to global setting for this doctor
    return await get_daily_limit(db, doctor_id)

@router.get("")
async def get_bookings(date: str = Query(None), doctor_id: str = Query(None), db: AsyncSession = Depends(get_db)):
    try:
        query = "SELECT id, patient_name, phone, notes, time, date, slot_id, doctor_id, is_paid FROM dashboard_bookings"
        conditions = []
        params = {}
        
        if not date:
            return [] # Safety: Don't return all bookings if date is missing
            
        conditions.append("date = :date")
        params["date"] = date
        
        if doctor_id:
            conditions.append("doctor_id = :doctor_id")
            params["doctor_id"] = doctor_id
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        result = await db.execute(text(query), params)
        
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
                "slot_id": row['slot_id'],
                "doctor_id": row.get('doctor_id', 'dr_1'),
                "is_paid": row.get('is_paid', False)
            })
        return bookings_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/settings")
async def get_settings(db: AsyncSession = Depends(get_db)):
    results = {}
    for doc_id in ['dr_1', 'dr_2', 'review']:
        results[doc_id] = await get_daily_limit(db, doc_id)
    return {"doctor_limits": results}

@router.post("/settings")
async def update_settings(settings: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    try:
        for doc_id, limit in settings.doctor_limits.items():
            key = f'daily_limit_{doc_id}'
            await db.execute(text("""
                INSERT INTO dashboard_settings (key, value) VALUES (:key, :val)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """), {"key": key, "val": str(limit)})
        await db.commit()
        return {"message": "Settings updated", "doctor_limits": settings.doctor_limits}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/month-stats")
async def get_month_stats(month: str = Query(...), db: AsyncSession = Depends(get_db)):
    """month format: YYYY-MM"""
    try:
        # Get global limits for both doctors
        doctor_limits = {}
        for doc_id in ['dr_1', 'dr_2', 'review']:
            doctor_limits[doc_id] = await get_daily_limit(db, doc_id)
        
        # Bookings count per date
        counts_res = await db.execute(text("""
            SELECT date, COUNT(*) as count 
            FROM dashboard_bookings 
            WHERE date LIKE :pattern
            GROUP BY date
        """), {"pattern": f"{month}-%"})
        counts = {row['date']: row['count'] for row in counts_res.mappings().all()}

        # Overrides per date and doctor
        limits_res = await db.execute(text("""
            SELECT date, doctor_id, limit_value 
            FROM dashboard_daily_limit 
            WHERE date LIKE :pattern
        """), {"pattern": f"{month}-%"})
        
        # Format overrides as {date: {doctor_id: limit}}
        limits_overrides = {}
        for row in limits_res.mappings().all():
            dt = row['date']
            if dt not in limits_overrides: limits_overrides[dt] = {}
            limits_overrides[dt][row['doctor_id']] = row['limit_value']

        return {
            "doctor_limits": doctor_limits, 
            "counts": counts, 
            "overrides": limits_overrides
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/daily-limit")
async def get_daily_limit_route(date: str = Query(...), doctor_id: str = Query('dr_1'), db: AsyncSession = Depends(get_db)):
    limit = await get_capacity_for_date(db, date, doctor_id)
    return {"date": date, "doctor_id": doctor_id, "limit": limit}

class DailyLimitUpdate(BaseModel):
    date: str
    doctor_id: str
    limit: int

@router.post("/daily-limit")
async def update_daily_limit(data: DailyLimitUpdate, db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("""
            INSERT INTO dashboard_daily_limit (date, doctor_id, limit_value) 
            VALUES (:date, :doctor_id, :limit)
            ON CONFLICT (date, doctor_id) DO UPDATE SET limit_value = EXCLUDED.limit_value
        """), {"date": data.date, "doctor_id": data.doctor_id, "limit": data.limit})
        await db.commit()
        return {"message": "Daily limit updated", "date": data.date, "doctor_id": data.doctor_id, "limit": data.limit}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics")
async def get_analytics(date: str = Query(None), db: AsyncSession = Depends(get_db)):
    try:
        from datetime import date as pydate
        today = date if date else pydate.today().isoformat()

        # Get capacities for today
        doc_capacities = {}
        total_limit_today = 0
        for doc_id in ['dr_1', 'dr_2', 'review']:
            cap = await get_capacity_for_date(db, today, doc_id)
            doc_capacities[doc_id] = cap
            total_limit_today += cap
        
        # Get global settings
        global_limits = {}
        for doc_id in ['dr_1', 'dr_2', 'review']:
            global_limits[doc_id] = await get_daily_limit(db, doc_id)

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
        daily_trends = [dict(row) for row in trends_res.mappings().all()]
        
        today_remaining = max(0, total_limit_today - today_booked)
        avg = round(total_total / len(daily_trends), 1) if daily_trends else 0
        
        return {
            "today_date": today,
            "today_booked": today_booked,
            "today_remaining": today_remaining,
            "daily_limit": total_limit_today, # Aggregate for aggregate cards
            "doctor_capacities": doc_capacities, # Individual breakdown
            "global_limits": global_limits,
            "total": total_total,
            "average_per_day": avg,
            "daily_trends": daily_trends
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")

@router.post("")
async def create_booking(booking: BookingCreate, db: AsyncSession = Depends(get_db)):
    try:
        # ID includes date, doctor and slot to allow same slot on different days/doctors
        doc_id = booking.doctor_id or "dr_1"
        booking_id = f"appt-{booking.date}-{doc_id}-{booking.slot_id}"
        
        result = await db.execute(text("SELECT id FROM dashboard_bookings WHERE id = :id"), {"id": booking_id})
        if result.fetchone():
            raise HTTPException(status_code=400, detail="Slot already booked for this doctor on this date")
            
        await db.execute(text("""
            INSERT INTO dashboard_bookings (id, patient_name, phone, notes, time, date, slot_id, doctor_id, is_paid)
            VALUES (:id, :name, :phone, :notes, :time, :date, :slot_id, :doctor_id, :is_paid)
        """), {
            "id": booking_id,
            "name": booking.patient_name,
            "phone": booking.patient_phone,
            "notes": booking.notes or "",
            "time": str(booking.slot_id),
            "date": booking.date,
            "slot_id": booking.slot_id,
            "doctor_id": doc_id,
            "is_paid": booking.is_paid
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
        if booking.doctor_id is not None:
            updates.append("doctor_id = :doctor_id")
            params["doctor_id"] = booking.doctor_id
        if booking.is_paid is not None:
            updates.append("is_paid = :is_paid")
            params["is_paid"] = booking.is_paid
            
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

class RescheduleRequest(BaseModel):
    new_date: str
    new_slot_id: int
    doctor_id: str

@router.post("/{booking_id}/reschedule")
async def reschedule_booking(booking_id: str, data: RescheduleRequest, db: AsyncSession = Depends(get_db)):
    try:
        # 1. Fetch existing booking
        res = await db.execute(text("SELECT * FROM dashboard_bookings WHERE id = :id"), {"id": booking_id})
        existing = res.mappings().first()
        if not existing:
            raise HTTPException(status_code=404, detail="Booking not found")

        # 2. Check if new slot is already taken
        new_id = f"appt-{data.new_date}-{data.doctor_id}-{data.new_slot_id}"
        conflict = await db.execute(text("SELECT id FROM dashboard_bookings WHERE id = :id"), {"id": new_id})
        if conflict.fetchone():
            raise HTTPException(status_code=400, detail="That slot is already booked")

        # 3. Delete old booking, insert at new slot (atomic)
        await db.execute(text("DELETE FROM dashboard_bookings WHERE id = :id"), {"id": booking_id})
        await db.execute(text("""
            INSERT INTO dashboard_bookings (id, patient_name, phone, notes, time, date, slot_id, doctor_id, is_paid)
            VALUES (:id, :name, :phone, :notes, :time, :date, :slot_id, :doctor_id, :is_paid)
        """), {
            "id": new_id,
            "name": existing["patient_name"],
            "phone": existing["phone"],
            "notes": existing["notes"],
            "time": str(data.new_slot_id),
            "date": data.new_date,
            "slot_id": data.new_slot_id,
            "doctor_id": data.doctor_id,
            "is_paid": existing["is_paid"]
        })
        await db.commit()
        return {"message": "Booking rescheduled successfully", "new_id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Reschedule failed: {str(e)}")
