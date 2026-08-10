"""backend/app/models/booking.py — Prenotazioni workshop."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey
from backend.app.config.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String(16), primary_key=True)          # BK-XXXX
    created_at = Column(String(32), nullable=False,
                        default=lambda: datetime.now(timezone.utc).isoformat())
    status = Column(String(32), nullable=False, default="pending")
    # pending | approved | paid | failed | cancelled | refunded | partially_refunded

    workshop_id = Column(String(64), ForeignKey("workshops.workshop_key"), nullable=True)
    workshop_name = Column(String(255), nullable=True)

    first_name = Column(String(128), nullable=False)
    last_name = Column(String(128), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(64), nullable=True)
    participants = Column(Integer, default=1)

    formula = Column(String(16), nullable=True)        # caparra | saldo

    # Importi in centesimi (evita floating point)
    original_cents = Column(Integer, nullable=True)
    discount_cents = Column(Integer, default=0)
    final_cents = Column(Integer, nullable=True)
    balance_cents = Column(Integer, default=0)
    amount_due_cents = Column(Integer, nullable=True)

    coupon_code = Column(String(64), nullable=True)

    # PayPal [ISOLATO]
    paypal_order_id = Column(String(64), nullable=True)
    paypal_capture_id = Column(String(64), nullable=True)
    paypal_env = Column(String(16), nullable=True)

    # Saldo in loco
    balance_paid = Column(Boolean, default=False)
    balance_paid_method = Column(String(32), nullable=True)
    balance_paid_date = Column(String(32), nullable=True)

    # Admin
    admin_notes = Column(Text, nullable=True)
    admin_status = Column(String(32), nullable=True)    # override stato manuale
    privacy_accepted = Column(Boolean, default=False)
    terms_accepted = Column(Boolean, default=False)
    cutoff_snapshot = Column(Boolean, default=False)    # incluso in snapshot cutoff

    # Soft delete
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(String(32), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "createdAt": self.created_at,
            "status": self.status,
            "workshopId": self.workshop_id,
            "workshopName": self.workshop_name,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "participants": self.participants,
            "formula": self.formula,
            "originalCents": self.original_cents,
            "discountCents": self.discount_cents,
            "finalCents": self.final_cents,
            "balanceCents": self.balance_cents,
            "amountDueCents": self.amount_due_cents,
            "couponCode": self.coupon_code,
            "paypalOrderId": self.paypal_order_id,
            "paypalCaptureId": self.paypal_capture_id,
            "paypalEnv": self.paypal_env,
            "balancePaid": self.balance_paid,
            "balancePaidMethod": self.balance_paid_method,
            "balancePaidDate": self.balance_paid_date,
            "adminNotes": self.admin_notes,
            "privacyAccepted": self.privacy_accepted,
            "termsAccepted": self.terms_accepted,
        }
