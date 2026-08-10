"""
backend/app/services/cutoff_service.py
Job di cutoff workshop:
  1. Chiude/segnala iscrizioni
  2. Crea snapshot immutabile partecipanti
  3. Genera XLSX
  4. Registra nel DB
  5. Idempotente (non genera duplicati)
  6. Schedulato con APScheduler
  7. Anche eseguibile manualmente dall'admin
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.config.database import SessionLocal, init_db
from backend.app.config.settings import settings
from backend.app.middleware.audit_log import log_action
from backend.app.models.booking import Booking
from backend.app.models.cost import WorkshopCost
from backend.app.models.report import Report
from backend.app.models.workshop import Workshop
from backend.app.services.excel_service import generate_xlsx


def run_cutoff(
    workshop_id: str,
    db: Session,
    triggered_by_user_id: Optional[int] = None,
    force: bool = False,
) -> dict:
    """
    Esegue il cutoff per un workshop.
    - force=False: idempotente, non rigenera se già eseguito.
    - force=True: genera una nuova versione del report.
    """
    ws = db.query(Workshop).filter(Workshop.workshop_key == workshop_id).first()
    if not ws:
        return {"status": "error", "message": f"Workshop '{workshop_id}' non trovato."}

    # Idempotenza: se il cutoff è già stato eseguito e non si forza, esci
    if ws.cutoff_status == "done" and not force:
        return {
            "status": "already_done",
            "message": f"Cutoff già eseguito per {workshop_id}. Usa force=True per rigenerare.",
            "workshopId": workshop_id,
        }

    ws.cutoff_status = "triggered"
    db.commit()

    try:
        # 1. Chiudi iscrizioni
        if ws.status == "active":
            ws.status = "soldout"  # o "completed" — configurabile
            ws.available_seats = 0

        # 2. Snapshot immutabile partecipanti (segna tutti i paid come snapshot)
        paid_bookings = (
            db.query(Booking)
            .filter(
                Booking.workshop_id == workshop_id,
                Booking.status == "paid",
                Booking.is_deleted.is_(False),
            )
            .all()
        )
        for b in paid_bookings:
            b.cutoff_snapshot = True
        db.commit()

        # 3. Carica costi
        cost = db.query(WorkshopCost).filter(WorkshopCost.workshop_id == workshop_id).first()

        # 4. Genera XLSX
        filepath, file_hash = generate_xlsx(
            workshop=ws,
            bookings=paid_bookings,
            cost=cost,
            output_dir=settings.exports_dir,
        )

        # 5. Nuova versione
        last_version = (
            db.query(Report)
            .filter(Report.workshop_id == workshop_id)
            .order_by(Report.version.desc())
            .first()
        )
        new_version = (last_version.version + 1) if last_version else 1

        # 6. Registra nel DB
        report = Report(
            workshop_id=workshop_id,
            version=new_version,
            generated_by=triggered_by_user_id,
            file_path=str(filepath),
            file_hash=file_hash,
            participant_count=len(paid_bookings),
            is_cutoff_snapshot=True,
            notes=f"Cutoff {'automatico' if not triggered_by_user_id else 'manuale'} v{new_version}",
        )
        db.add(report)

        # 7. Aggiorna workshop
        ws.cutoff_status = "done"
        ws.report_generated_at = datetime.now(timezone.utc).isoformat()
        ws.report_version = new_version
        db.commit()

        # 8. Audit log
        log_action(
            db,
            action="cutoff_executed",
            user_id=triggered_by_user_id,
            resource_type="workshop",
            resource_id=workshop_id,
            details={
                "version": new_version,
                "participantCount": len(paid_bookings),
                "forced": force,
            },
        )

        return {
            "status": "success",
            "workshopId": workshop_id,
            "version": new_version,
            "participantCount": len(paid_bookings),
            "reportPath": str(filepath),
        }

    except Exception as e:
        ws.cutoff_status = "error"
        db.commit()
        log_action(db, "cutoff_error", resource_type="workshop", resource_id=workshop_id,
                   details={"error": type(e).__name__})
        return {
            "status": "error",
            "message": f"Errore durante il cutoff: {type(e).__name__}: {str(e)[:200]}",
        }


def check_and_run_pending_cutoffs() -> None:
    """
    Controlla tutti i workshop con cutoff_at nel passato e status 'pending'.
    Chiamato dallo scheduler APScheduler.
    IDEMPOTENTE: usa transaction con controllo cutoff_status.
    """
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc).isoformat()
        pending = (
            db.query(Workshop)
            .filter(
                Workshop.cutoff_at.isnot(None),
                Workshop.cutoff_at <= now,
                Workshop.cutoff_status == "pending",
            )
            .all()
        )

        for ws in pending:
            print(f"[Cutoff] Esecuzione automatica per: {ws.workshop_key}")
            result = run_cutoff(ws.workshop_key, db, triggered_by_user_id=None, force=False)
            print(f"[Cutoff] Risultato: {result}")

    finally:
        db.close()


def setup_scheduler():
    """Configura e avvia APScheduler per i cutoff automatici."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        scheduler = BackgroundScheduler(timezone="UTC")
        scheduler.add_job(
            func=check_and_run_pending_cutoffs,
            trigger=IntervalTrigger(minutes=5),
            id="cutoff_check",
            name="Controllo cutoff workshop",
            replace_existing=True,
            coalesce=True,       # se si accumula lag, esegui una sola volta
            max_instances=1,     # nessuna sovrapposizione
        )
        scheduler.start()
        print("[Scheduler] APScheduler avviato. Controllo cutoff ogni 5 minuti.")
        return scheduler
    except ImportError:
        print("[Scheduler] APScheduler non disponibile. Installa: pip install APScheduler")
        return None
