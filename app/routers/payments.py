import random
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.logging import get_logger
from app.deps import get_current_user
from app.models.models import (
    Booking, Payment, User, BookingStatus, PaymentStatus, WebhookEvent,
)
from app.schemas.schemas import PaymentCreate, PaymentOut, WebhookPayload

router = APIRouter(prefix="/payments", tags=["payments"])
logger = get_logger(__name__)


@router.post("/", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def make_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Simulated synchronous payment. In real life this would call out to a
    payment gateway; here we just flip a weighted coin.
    """
    booking = db.get(Booking, payload.booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your booking")
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Booking is not payable in its current state: {booking.status.value}",
        )

    succeeded = random.random() < settings.SIMULATED_PAYMENT_SUCCESS_RATE

    payment = Payment(
        booking_id=booking.id,
        amount=booking.amount,
        status=PaymentStatus.SUCCESS if succeeded else PaymentStatus.FAILED,
        provider_reference=str(uuid.uuid4()),
    )
    booking.status = BookingStatus.CONFIRMED if succeeded else BookingStatus.FAILED

    db.add(payment)
    db.commit()
    db.refresh(payment)
    logger.info(
        "Payment %s for booking %s: %s",
        payment.id, booking.id, payment.status.value,
    )
    return payment


@router.post("/webhook/", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
def payment_webhook(request: Request, payload: WebhookPayload, db: Session = Depends(get_db)):
    """
    Idempotent webhook receiver for a simulated payment provider.

    **Idempotency strategy** — all writes (``WebhookEvent`` insert,
    ``Payment`` insert, ``Booking`` status update) happen in a **single
    database transaction**:

    1. Build the ``WebhookEvent``, ``Payment``, and ``Booking`` update.
    2. ``commit()`` them atomically.
    3. If ``event_id`` violates the unique constraint → ``IntegrityError``
       → rollback → return ``already_processed`` without any side-effects.

    This avoids the crash-window that would exist if the event claim and the
    payment/booking update were committed separately.
    """
    # Fast path: if we already processed this event, skip object creation.
    # This is an optimisation; the unique constraint below is the real
    # correctness guarantee.
    existing = (
        db.query(WebhookEvent)
        .filter(WebhookEvent.event_id == payload.event_id)
        .first()
    )
    if existing:
        logger.info("Webhook event %s already processed — skipping", payload.event_id)
        return {"status": "already_processed", "event_id": payload.event_id}

    booking = db.get(Booking, payload.booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    # Build all mutations, then commit them as one atomic transaction.
    event = WebhookEvent(event_id=payload.event_id, payload=payload.model_dump_json())
    payment = Payment(
        booking_id=booking.id,
        amount=booking.amount,
        status=payload.status,
        provider_reference=payload.provider_reference,
    )

    if payload.status == PaymentStatus.SUCCESS:
        booking.status = BookingStatus.CONFIRMED
    elif payload.status == PaymentStatus.FAILED:
        booking.status = BookingStatus.FAILED

    db.add(event)
    db.add(payment)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.info("Webhook event %s duplicate caught by constraint", payload.event_id)
        return {"status": "already_processed", "event_id": payload.event_id}

    logger.info(
        "Webhook processed: event=%s booking=%s → %s",
        payload.event_id, booking.id, booking.status.value,
    )
    return {"status": "processed", "event_id": payload.event_id, "booking_status": booking.status}


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment(
    payment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    if payment.booking.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your payment")
    return payment
