import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Numeric, ForeignKey, DateTime, Enum, UniqueConstraint, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


def utcnow():
    return datetime.now(timezone.utc)


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    bookings = relationship("Booking", back_populates="user")


class DiagnosticCentre(Base):
    __tablename__ = "diagnostic_centres"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    tests = relationship("DiagnosticTest", back_populates="centre", cascade="all, delete-orphan")


class DiagnosticTest(Base):
    __tablename__ = "diagnostic_tests"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    centre_id = Column(UUID(as_uuid=False), ForeignKey("diagnostic_centres.id"), nullable=False)
    name = Column(String, nullable=False)
    price = Column(Numeric(10, 2, asdecimal=False), nullable=False)

    centre = relationship("DiagnosticCentre", back_populates="tests")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    test_id = Column(UUID(as_uuid=False), ForeignKey("diagnostic_tests.id"), nullable=False)
    centre_id = Column(UUID(as_uuid=False), ForeignKey("diagnostic_centres.id"), nullable=False)
    appointment_time = Column(DateTime(timezone=True), nullable=False)
    amount = Column(Numeric(10, 2, asdecimal=False), nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="bookings")
    test = relationship("DiagnosticTest")
    centre = relationship("DiagnosticCentre")
    payments = relationship("Payment", back_populates="booking")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    booking_id = Column(UUID(as_uuid=False), ForeignKey("bookings.id"), nullable=False)
    amount = Column(Numeric(10, 2, asdecimal=False), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    provider_reference = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    booking = relationship("Booking", back_populates="payments")


class WebhookEvent(Base):
    """
    Records every webhook event we have processed, keyed by the provider's
    unique event id. This is what makes the webhook endpoint idempotent:
    if event_id already exists, we short-circuit and return the stored
    result instead of re-applying side effects.
    """
    __tablename__ = "webhook_events"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    event_id = Column(String, unique=True, nullable=False, index=True)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (UniqueConstraint("event_id", name="uq_webhook_event_id"),)
