"""backend/app/models/coupon.py — Codici sconto con Decimal e validazione rigorosa."""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey
from backend.app.config.database import Base

# Tipi ammessi esattamente due:
COUPON_TYPE_PERCENTAGE  = "percentage"    # valore 0-100%
COUPON_TYPE_FINAL_PRICE = "final_price"   # prezzo finale fisso


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, nullable=False, index=True)  # sempre uppercase
    description = Column(String(512), nullable=True)
    status = Column(String(16), default="active", nullable=False)  # active | inactive

    # Tipo: SOLO 'percentage' o 'final_price'
    type = Column(String(16), nullable=False)

    # Valore salvato come stringa per preservare precisione Decimal
    # percentage: 0-100, final_price: importo in euro (es. "300.00")
    value_decimal = Column(String(32), nullable=False)

    # Date validità (ISO date string YYYY-MM-DD)
    start_date = Column(String(10), nullable=True)
    end_date = Column(String(10), nullable=True)

    # Workshop applicabili (JSON: ["all"] o ["friuli-2026", ...])
    applicable_workshops = Column(Text, nullable=True, default='["all"]')

    # Limiti utilizzo
    max_uses_total = Column(Integer, nullable=True)
    max_uses_per_email = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0, nullable=False)

    # Audit
    created_at = Column(String(32), nullable=False,
                        default=lambda: datetime.now(timezone.utc).isoformat())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(String(32), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    @property
    def value(self) -> Decimal:
        """Valore come Decimal (mai float)."""
        return Decimal(self.value_decimal)

    def is_active(self) -> bool:
        return self.status == "active"

    def is_expired(self) -> bool:
        today = datetime.now(timezone.utc).date().isoformat()
        return bool(self.end_date and self.end_date < today)

    def is_not_yet_active(self) -> bool:
        today = datetime.now(timezone.utc).date().isoformat()
        return bool(self.start_date and self.start_date > today)

    def is_exhausted(self) -> bool:
        return (self.max_uses_total is not None and
                self.used_count >= self.max_uses_total)

    def to_dict(self, include_sensitive: bool = True) -> dict:
        d: dict = {
            "id": self.id,
            "code": self.code,
            "type": self.type,
            "valueDecimal": self.value_decimal,
            "status": self.status,
            "startDate": self.start_date,
            "endDate": self.end_date,
            "maxUsesTotal": self.max_uses_total,
            "maxUsesPerEmail": self.max_uses_per_email,
            "usedCount": self.used_count,
            "createdAt": self.created_at,
        }
        if include_sensitive:
            d["description"] = self.description
            d["applicableWorkshops"] = self.applicable_workshops
            d["updatedAt"] = self.updated_at
        return d
