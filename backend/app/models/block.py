"""backend/app/models/block.py — Blocchi CMS ordinabili per ogni pagina."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey
from backend.app.config.database import Base

# Tipi di blocco supportati (whitelist — non aggiungere senza revisione CSS)
BLOCK_TYPES = {
    "heading", "subheading", "text", "richtext", "quote",
    "image", "gallery", "video", "cta", "list", "table",
    "faq", "separator", "hero", "workshop_card", "program",
    "requirements", "cancellation_policy", "contacts",
}

# Varianti consentite per tipo
BLOCK_VARIANTS: dict[str, list[str]] = {
    "heading":    ["h1", "h2", "h3"],
    "cta":        ["primary", "secondary", "outline"],
    "separator":  ["thin", "thick", "gradient"],
    "hero":       ["full", "compact"],
    "image":      ["full", "contained", "float-right", "float-left"],
    "gallery":    ["grid-2", "grid-3", "masonry"],
}


class Block(Base):
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True)

    # ID stabile per riferimenti (UUID v4, non cambia mai)
    block_key = Column(String(64), unique=True, nullable=False)

    type = Column(String(32), nullable=False)
    content = Column(Text, nullable=False, default="{}")    # JSON sanitizzato
    order_index = Column(Integer, nullable=False, default=0)
    is_visible = Column(Boolean, default=True, nullable=False)
    variant = Column(String(32), nullable=True)             # dalla whitelist BLOCK_VARIANTS
    responsive_settings = Column(Text, nullable=True)       # JSON validato (no JS)

    updated_at = Column(String(32), nullable=False,
                        default=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pageId": self.page_id,
            "blockKey": self.block_key,
            "type": self.type,
            "content": self.content,
            "orderIndex": self.order_index,
            "isVisible": self.is_visible,
            "variant": self.variant,
            "responsiveSettings": self.responsive_settings,
            "updatedAt": self.updated_at,
        }
