from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Boolean, Numeric, func, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint('clinic_id', 'doctor_id', 'start_ts', name='uq_booking_slot'),
    )

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"))
    patient_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    start_ts = Column(DateTime(timezone=True), nullable=False)
    end_ts = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), server_default="pending")
    stripe_payment_intent = Column(String(255), nullable=True)
    amount = Column(Numeric(10,2))
    cancelled = Column(Boolean, server_default="false")

    clinic = relationship("Clinic")
    doctor = relationship("Doctor")
    patient = relationship("User")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
