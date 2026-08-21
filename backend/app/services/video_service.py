"""
backend/app/services/video_service.py
Pipeline video asincrona per il Web con FFmpeg e FFprobe.
- Verifica formato reale, durata e dimensioni
- Codifica H.264 Web-friendly con -movflags +faststart
- Audio AAC
- Versioni 1080p e 720p (senza upscaling)
- Supporto video verticali preservando il rapporto
- Generazione poster WebP e JPEG
- Esecuzione sicura subprocess con lista argomenti
- Pulizia file temporanei
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from backend.app.config.settings import settings
from backend.app.models.job import Job
from backend.app.models.media import Media


def is_ffmpeg_available() -> Tuple[bool, bool]:
    """Verifica se ffmpeg ed ffprobe sono installati e accessibili."""
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    ffprobe_ok = shutil.which("ffprobe") is not None
    return ffmpeg_ok, ffprobe_ok


def probe_video_file(file_path: Path) -> Dict[str, Any]:
    """Esegue ffprobe in modo sicuro per estrarre metadati video."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def process_video_job_sync(job_id: str, db_factory) -> None:
    """Funzione di elaborazione video eseguita nel job in background."""
    db: Session = db_factory()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return

    job.status = "processing"
    job.started_at = datetime.now(timezone.utc).isoformat()
    job.progress_percent = 10
    db.commit()

    meta = json.loads(job.metadata_json or "{}")
    temp_input_path = Path(meta.get("tempInputPath", ""))
    original_filename = meta.get("originalFilename", "video.mp4")
    user_id = job.created_by_user_id

    try:
        if not temp_input_path.exists():
            raise FileNotFoundError(f"File temporaneo non trovato: {temp_input_path}")

        ffmpeg_ok, ffprobe_ok = is_ffmpeg_available()
        if not (ffmpeg_ok and ffprobe_ok):
            raise RuntimeError("FFmpeg o FFprobe non sono installati sul server.")

        # 1. Analisi metadati video
        probe_data = probe_video_file(temp_input_path)
        video_stream = next((s for s in probe_data.get("streams", []) if s.get("codec_type") == "video"), None)
        if not video_stream:
            raise ValueError("Il file caricato non contiene un flusso video valido.")

        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        duration = float(probe_data.get("format", {}).get("duration", 0))

        # Gestione rotazione nei metadati (video verticali)
        tags = video_stream.get("tags", {})
        rotation = int(tags.get("rotate", 0))
        if rotation in (90, 270):
            width, height = height, width

        is_vertical = (height > width)
        job.progress_percent = 30
        db.commit()

        # 2. Output directory
        output_dir = settings.public_upload_dir / "videos"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        base_name = f"vid_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{job_id[:8]}"
        out_1080p = output_dir / f"{base_name}_1080p.mp4"
        out_720p = output_dir / f"{base_name}_720p.mp4"
        poster_jpg = output_dir / f"{base_name}_poster.jpg"
        poster_webp = output_dir / f"{base_name}_poster.webp"

        # 3. Generazione poster al secondo 1.0 (o a metà durata)
        poster_time = min(1.0, max(0.0, duration / 2))
        cmd_poster = [
            "ffmpeg", "-y",
            "-ss", str(poster_time),
            "-i", str(temp_input_path),
            "-vframes", "1",
            "-q:v", "2",
            str(poster_jpg),
        ]
        subprocess.run(cmd_poster, capture_output=True, check=True)

        cmd_poster_webp = [
            "ffmpeg", "-y",
            "-i", str(poster_jpg),
            "-quality", "85",
            str(poster_webp),
        ]
        subprocess.run(cmd_poster_webp, capture_output=True, check=False)

        job.progress_percent = 50
        db.commit()

        # 4. Codifica 1080p (o risoluzione originale se inferiore)
        # Filtro scala mantenendo proporzioni senza upscaling e forzando divisibilità per 2 (yuv420p)
        if is_vertical:
            scale_1080 = "scale=-2:'min(1920,ih)':flags=lanczos"
        else:
            scale_1080 = "scale='min(1920,iw)':-2:flags=lanczos"

        cmd_1080p = [
            "ffmpeg", "-y",
            "-i", str(temp_input_path),
            "-vf", scale_1080,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            str(out_1080p),
        ]
        subprocess.run(cmd_1080p, capture_output=True, check=True)

        job.progress_percent = 80
        db.commit()

        # 5. Codifica 720p fallback se il video originale è sufficientemente grande
        has_720p = False
        if max(width, height) >= 1280:
            if is_vertical:
                scale_720 = "scale=-2:'min(1280,ih)':flags=lanczos"
            else:
                scale_720 = "scale='min(1280,iw)':-2:flags=lanczos"

            cmd_720p = [
                "ffmpeg", "-y",
                "-i", str(temp_input_path),
                "-vf", scale_720,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "25",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "96k",
                "-movflags", "+faststart",
                str(out_720p),
            ]
            subprocess.run(cmd_720p, capture_output=True, check=True)
            has_720p = True

        job.progress_percent = 95
        db.commit()

        # 6. Registra il media nel DB
        media = Media(
            original_filename=original_filename,
            stored_filename=out_1080p.name,
            mime_type="video/mp4",
            width=width,
            height=height,
            file_size_bytes=out_1080p.stat().st_size,
            hash_sha256=job_id,
            alt_text=meta.get("altText", f"Video {original_filename}"),
            caption=meta.get("caption"),
            page_tag=meta.get("pageTag", "general"),
            jpeg_path=f"/assets/upload/videos/{poster_jpg.name}" if poster_jpg.exists() else None,
            webp_path=f"/assets/upload/videos/{poster_webp.name}" if poster_webp.exists() else None,
            variants=json.dumps({
                "1080p": f"/assets/upload/videos/{out_1080p.name}",
                "720p": f"/assets/upload/videos/{out_720p.name}" if has_720p else None,
                "posterJpg": f"/assets/upload/videos/{poster_jpg.name}" if poster_jpg.exists() else None,
                "posterWebp": f"/assets/upload/videos/{poster_webp.name}" if poster_webp.exists() else None,
                "duration": round(duration, 2),
                "isVertical": is_vertical,
            }),
            uploaded_by=user_id,
        )
        db.add(media)

        # 7. Completa il job
        job.status = "completed"
        job.progress_percent = 100
        job.completed_at = datetime.now(timezone.utc).isoformat()
        db.commit()

    except Exception as exc:
        job.status = "error"
        job.error_summary = str(exc)[:500]
        job.completed_at = datetime.now(timezone.utc).isoformat()
        db.commit()
    finally:
        # Pulisce sempre il file temporaneo
        if temp_input_path.exists():
            try:
                temp_input_path.unlink()
            except Exception:
                pass
        db.close()