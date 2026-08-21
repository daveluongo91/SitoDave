"""
backend/app/routes/participants.py
Gestione partecipanti — SOLO admin autenticati.
Dati personali: minimizzati nell'output, nessun log personale.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.config.database import get_db
from backend.app.middleware.auth import get_admin_user, require_role
from backend.app.middleware.audit_log import log_action
from backend.app.middleware.csrf import verify_csrf
from backend.app.models.user import User
from backend.app.models.booking import Booking
from datetime import datetime, timezone

router = APIRouter(prefix="/api/admin/participants", tags=["admin-participants"])


@router.get("/")
async def list_participants(
    workshopId: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Lista partecipanti, opzionalmente filtrati per workshop."""
    query = db.query(Booking).filter(Booking.is_deleted.is_(False))
    if workshopId:
        query = query.filter(Booking.workshop_id == workshopId)
    if status:
        query = query.filter(Booking.status == status)
    bookings = query.order_by(Booking.created_at.desc()).all()
    return {"participants": [b.to_dict() for b in bookings]}


@router.get("/export")
async def export_participants(
    request: Request,
    workshopId: Optional[str] = None,
    filterType: Optional[str] = "all",  # all | paid | caparra | saldo | pending | cancelled | refunded | balance_pending
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    Export estemporaneo dei partecipanti in formato XLSX.
    Disponibile in qualsiasi momento: non modifica lo stato del cutoff e non tocca le prenotazioni.
    """
    from fastapi.responses import FileResponse
    from backend.app.models.workshop import Workshop
    from backend.app.models.cost import WorkshopCost
    from backend.app.services.export_service import generate_participants_export_xlsx

    query = db.query(Booking).filter(Booking.is_deleted.is_(False))

    ws = None
    if workshopId:
        ws = db.query(Workshop).filter(Workshop.workshop_key == workshopId).first()
        query = query.filter(Booking.workshop_id == workshopId)

    # Filtro tipologia / stato
    filter_labels = {
        "all": "Tutti",
        "paid": "Solo Pagati",
        "caparra": "Caparra Versata",
        "saldo": "Saldo Completo",
        "pending": "In Attesa",
        "cancelled": "Annullati",
        "refunded": "Rimborsati",
        "balance_pending": "Saldo Ancora da Riscuotere",
    }
    filter_label = filter_labels.get(filterType, "Personalizzato")

    if filterType == "paid":
        query = query.filter(Booking.status == "paid")
    elif filterType == "caparra":
        query = query.filter(Booking.status == "paid", Booking.formula == "caparra")
    elif filterType == "saldo":
        query = query.filter(Booking.status == "paid", Booking.formula == "saldo")
    elif filterType == "pending":
        query = query.filter(Booking.status == "pending")
    elif filterType == "cancelled":
        query = query.filter(Booking.status == "cancelled")
    elif filterType == "refunded":
        query = query.filter(Booking.status.in_(["refunded", "partially_refunded"]))
    elif filterType == "balance_pending":
        query = query.filter(
            Booking.status == "paid",
            Booking.formula == "caparra",
            Booking.balance_paid.is_(False),
        )

    # Filtri intervallo date (created_at ISO string)
    if startDate:
        query = query.filter(Booking.created_at >= startDate)
        filter_label += f" • Da: {startDate}"
    if endDate:
        query = query.filter(Booking.created_at <= (endDate + "T23:59:59"))
        filter_label += f" • A: {endDate}"

    bookings = query.order_by(Booking.created_at.asc()).all()

    cost = None
    if ws:
        cost = db.query(WorkshopCost).filter(WorkshopCost.workshop_id == ws.workshop_key).first()

    filepath, file_hash, filename = generate_participants_export_xlsx(
        workshop=ws,
        bookings=bookings,
        cost=cost,
        filter_label=filter_label,
    )

    # Audit log (SOLO metadati, nessun dato personale)
    log_action(
        db,
        action="participants_export",
        user_id=current_user.id,
        resource_type="export",
        resource_id=workshopId or "all",
        details={
            "workshopId": workshopId or "all",
            "filterType": filterType,
            "count": len(bookings),
            "filename": filename,
        },
        ip=request.client.host if request.client else None,
    )

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



@router.get("/{booking_id}")
async def get_participant(
    booking_id: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    b = db.query(Booking).filter(Booking.id == booking_id, Booking.is_deleted.is_(False)).first()
    if not b:
        raise HTTPException(status_code=404, detail="Prenotazione non trovata.")
    return b.to_dict()


class AdminNoteUpdate(BaseModel):
    adminNotes: Optional[str] = None
    adminStatus: Optional[str] = None


@router.put("/{booking_id}", dependencies=[Depends(verify_csrf)])
async def update_participant(
    request: Request,
    booking_id: str,
    body: AdminNoteUpdate,
    current_user: User = Depends(require_role("editor")),
    db: Session = Depends(get_db),
):
    """Aggiorna note amministrative di una prenotazione."""
    b = db.query(Booking).filter(Booking.id == booking_id, Booking.is_deleted.is_(False)).first()
    if not b:
        raise HTTPException(status_code=404, detail="Prenotazione non trovata.")

    if body.adminNotes is not None:
        b.admin_notes = body.adminNotes[:2000]
    if body.adminStatus is not None:
        b.admin_status = body.adminStatus

    db.commit()
    log_action(db, "participant_update", user_id=current_user.id,
               resource_type="booking", resource_id=booking_id,
               ip=request.client.host if request.client else None)
    return b.to_dict()


class BalancePaidRequest(BaseModel):
    method: str = "contanti"  # bonifico | contanti | paypal


@router.post("/{booking_id}/mark-balance-paid", dependencies=[Depends(verify_csrf)])
async def mark_balance_paid(
    request: Request,
    booking_id: str,
    body: BalancePaidRequest,
    current_user: User = Depends(require_role("editor")),
    db: Session = Depends(get_db),
):
    """Segna il saldo di una prenotazione come pagato in loco."""
    b = db.query(Booking).filter(Booking.id == booking_id, Booking.is_deleted.is_(False)).first()
    if not b:
        raise HTTPException(status_code=404, detail="Prenotazione non trovata.")

    allowed_methods = {"bonifico", "contanti", "paypal", "altro"}
    if body.method not in allowed_methods:
        raise HTTPException(status_code=400, detail=f"Metodo non valido. Ammessi: {', '.join(allowed_methods)}")

    b.balance_paid = True
    b.balance_paid_method = body.method
    b.balance_paid_date = datetime.now(timezone.utc).isoformat()
    db.commit()

    log_action(db, "balance_paid", user_id=current_user.id,
               resource_type="booking", resource_id=booking_id,
               details={"method": body.method},
               ip=request.client.host if request.client else None)
    return {"status": "ok", "message": "Saldo segnato come pagato."}


@router.delete("/{booking_id}", dependencies=[Depends(verify_csrf)])
async def soft_delete_participant(
    request: Request,
    booking_id: str,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Soft delete: marca la prenotazione come eliminata (non cancella dal DB)."""
    b = db.query(Booking).filter(Booking.id == booking_id, Booking.is_deleted.is_(False)).first()
    if not b:
        raise HTTPException(status_code=404, detail="Prenotazione non trovata.")

    b.is_deleted = True
    b.deleted_at = datetime.now(timezone.utc).isoformat()
    db.commit()

    log_action(db, "participant_soft_delete", user_id=current_user.id,
               resource_type="booking", resource_id=booking_id,
               ip=request.client.host if request.client else None)
    return {"status": "ok", "message": "Prenotazione eliminata (soft delete)."}
