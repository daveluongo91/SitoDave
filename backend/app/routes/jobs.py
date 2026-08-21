"""
backend/app/routes/jobs.py
Router per il monitoraggio dei job asincroni (elaborazione video, cutoff, backup, import/export CSV).
Solo admin autenticati.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.config.database import get_db
from backend.app.middleware.auth import get_admin_user
from backend.app.models.job import Job
from backend.app.models.user import User

router = APIRouter(prefix="/api/admin/jobs", tags=["admin-jobs"])


@router.get("/")
async def list_jobs(
    type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Restituisce l'elenco dei job recenti."""
    query = db.query(Job)
    if type:
        query = query.filter(Job.type == type)
    if status:
        query = query.filter(Job.status == status)

    jobs = query.order_by(desc(Job.created_at)).limit(50).all()
    return {"jobs": [j.to_dict() for j in jobs]}


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Restituisce lo stato corrente di un job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job non trovato.")
    return job.to_dict()