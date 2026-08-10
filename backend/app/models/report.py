"""backend/app/models/report.py — Report XLSX generati al cutoff."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Integer, String, ForeignKey
from backend.app.config.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    workshop_id = Column(String(64), ForeignKey("workshops.workshop_key"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    generated_at = Column(String(32), nullable=False,
                          default=lambda: datetime.now(timezone.utc).isoformat())
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Percorso nella directory private/exports/ (non pubblica)
    file_path = Column(String(512), nullable=False)
    file_hash = Column(String(64), nullable=False)            # SHA256

    participant_count = Column(Integer, nullable=True)
    is_cutoff_snapshot = Column(Boolean, default=False)       # True = generato automaticamente al cutoff
    notes = Column(String(512), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workshopId": self.workshop_id,
            "version": self.version,
            "generatedAt": self.generated_at,
            "generatedBy": self.generated_by,
            "fileHash": self.file_hash,
            "participantCount": self.participant_count,
            "isCutoffSnapshot": self.is_cutoff_snapshot,
            "notes": self.notes,
        }
