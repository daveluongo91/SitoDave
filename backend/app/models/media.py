"""backend/app/models/media.py — Libreria immagini con deduplicazione e varianti."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey, Float
from backend.app.config.database import Base


class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), unique=True, nullable=False)   # sicuro, server-side
    mime_type = Column(String(64), nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    hash_sha256 = Column(String(64), unique=True, nullable=True, index=True)  # deduplicazione

    # Accessibilità
    alt_text = Column(String(512), nullable=True)     # obbligatorio per immagini informative
    caption = Column(String(512), nullable=True)

    # Focal point (0.0 - 1.0)
    focal_point_x = Column(Float, default=0.5)
    focal_point_y = Column(Float, default=0.5)

    # Classificazione
    tags = Column(Text, nullable=True)                # JSON array
    page_tag = Column(String(64), nullable=True)      # pagina di appartenenza
    is_private = Column(Boolean, default=False)       # non servibile pubblicamente

    # Percorsi output
    webp_path = Column(String(512), nullable=True)
    jpeg_path = Column(String(512), nullable=True)
    variants = Column(Text, nullable=True)            # JSON {480: path, 768: path, ...}

    # Audit
    uploaded_at = Column(String(32), nullable=False,
                         default=lambda: datetime.now(timezone.utc).isoformat())
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_deleted = Column(Boolean, default=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "originalFilename": self.original_filename,
            "storedFilename": self.stored_filename,
            "mimeType": self.mime_type,
            "width": self.width,
            "height": self.height,
            "fileSizeBytes": self.file_size_bytes,
            "altText": self.alt_text,
            "caption": self.caption,
            "focalPointX": self.focal_point_x,
            "focalPointY": self.focal_point_y,
            "tags": self.tags,
            "pageTag": self.page_tag,
            "webpPath": self.webp_path,
            "jpegPath": self.jpeg_path,
            "variants": self.variants,
            "uploadedAt": self.uploaded_at,
        }
