"""backend/app/models/job.py — Tracciamento job in background e manutenzione."""
from __future__ import annotations

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from backend.app.config.database import Base


class Job(Base):
    __tablename__ = "background_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Tipo: cutoff | video_processing | export | import_csv | backup | cleanup
    type = Column(String(32), nullable=False, index=True)
    
    # Stato: pending | processing | completed | error
    status = Column(String(32), nullable=False, default="pending", index=True)
    progress_percent = Column(Integer, nullable=False, default=0)

    created_at = Column(String(32), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    started_at = Column(String(32), nullable=True)
    completed_at = Column(String(32), nullable=True)

    # Messaggio di errore sintetico (privo di dati personali)
    error_summary = Column(Text, nullable=True)
    
    # Metadati tecnici in JSON (es. input_path, output_path, resolution, records_count)
    metadata_json = Column(Text, nullable=True)
    
    attempts = Column(Integer, nullable=False, default=0)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "progressPercent": self.progress_percent,
            "createdAt": self.created_at,
            "startedAt": self.started_at,
            "completedAt": self.completed_at,
            "errorSummary": self.error_summary,
            "metadata": self.metadata_json,
            "attempts": self.attempts,
            "createdByUserId": self.created_by_user_id,
        }