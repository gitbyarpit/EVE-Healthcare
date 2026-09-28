from datetime import datetime, timezone
from typing import Generic, TypeVar

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

from app.models.models import BookingStatus, PaymentStatus

T = TypeVar("T")


# ---------- Pagination ----------

class PaginatedResponse(BaseModel, Generic[T]):
    """Wrapper that pairs a page of results with pagination metadata."""

    items: list[T]
    total: int
    skip: int
    limit: int
    has_next: bool


# ---------- Auth ----------

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Centres & Tests ----------

class TestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    price: float


class TestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price: float = Field(gt=0)


class CentreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=200)


class CentreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    location: str
    tests: list[TestOut] = []


# ---------- Bookings ----------

class BookingCreate(BaseModel):
    test_id: str
    appointment_time: datetime

    @field_validator("appointment_time")
    @classmethod
    def must_be_in_future(cls, v: datetime) -> datetime:
        # Treat naive datetimes as UTC for safety.
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= datetime.now(timezone.utc):
            raise ValueError("appointment_time must be in the future")
        return v


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    test_id: str
    centre_id: str
    appointment_time: datetime
    amount: float
    status: BookingStatus
    created_at: datetime


# ---------- Payments ----------

class PaymentCreate(BaseModel):
    booking_id: str


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    booking_id: str
    amount: float
    status: PaymentStatus
    provider_reference: str | None = None


class WebhookPayload(BaseModel):
    """
    Simulated payment-provider webhook payload.
    ``event_id`` must be unique per real-world event; the provider may resend
    the same event_id on retry, which is exactly what must stay idempotent.
    """

    event_id: str = Field(min_length=1)
    booking_id: str
    status: PaymentStatus
    provider_reference: str | None = None
