"""
backend/app/services/image_service.py
Pipeline immagini completa:
  1. Verifica formato e MIME reale
  2. Limita dimensioni e decompression bomb
  3. Orientamento EXIF
  4. Ridimensiona max 2048px (no upscale)
  5. Converti sRGB
  6. Rimuovi metadati / GPS
  7. Genera WebP + JPEG fallback
  8. Varianti responsive: 480, 768, 1280, 2048
  9. Qualità progressiva se output > 5MB
  10. Hash SHA256 per deduplicazione
  11. Nome file sicuro server-side
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import secrets
import struct
from pathlib import Path
from typing import Optional

from backend.app.config.settings import settings

try:
    from PIL import Image, ImageCms, ImageOps
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Varianti responsive (larghezza in px)
RESPONSIVE_WIDTHS = [480, 768, 1280, 2048]

# MIME types ammessi (verificati sul contenuto, non solo estensione)
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/tiff"}

# Magic bytes per verifica MIME reale
MAGIC_BYTES = {
    b"\xff\xd8\xff":        "image/jpeg",
    b"\x89PNG\r\n\x1a\n":  "image/png",
    b"RIFF":                "image/webp",   # + 'WEBP' a offset 8
    b"GIF87a":              "image/gif",
    b"GIF89a":              "image/gif",
    b"II*\x00":             "image/tiff",
    b"MM\x00*":             "image/tiff",
}

# Limite pixel decodificati (anti decompression bomb: 100 MP)
MAX_PIXELS = 100_000_000


def detect_mime(data: bytes) -> Optional[str]:
    """Verifica il MIME type dal contenuto reale del file (non dall'estensione)."""
    for magic, mime in MAGIC_BYTES.items():
        if data[:len(magic)] == magic:
            if mime == "image/webp" and len(data) >= 12 and data[8:12] != b"WEBP":
                continue
            return mime
    return None


def _safe_filename(original_name: str) -> str:
    """Genera un nome file sicuro e univoco lato server."""
    stem = Path(original_name).stem
    # Rimuovi caratteri non sicuri
    clean = re.sub(r"[^\w\-]", "_", stem)[:32].strip("_") or "image"
    token = secrets.token_hex(8)
    return f"{clean}_{token}"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _save_variant(img: Image.Image, width: int, base_dir: Path, base_name: str, quality: int) -> dict:
    """Salva una variante responsive in WebP e JPEG."""
    if img.width <= width:
        # Non ingrandire
        variant_img = img
        actual_w = img.width
    else:
        ratio = width / img.width
        actual_w = width
        actual_h = max(1, round(img.height * ratio))
        variant_img = img.resize((actual_w, actual_h), Image.Resampling.LANCZOS)

    safe_q = max(settings.image_quality_min, quality)
    webp_path = base_dir / f"{base_name}_{actual_w}w.webp"
    jpeg_path = base_dir / f"{base_name}_{actual_w}w.jpg"

    # sRGB ICC profile
    srgb_profile = ImageCms.createProfile("sRGB")
    srgb_bytes = ImageCms.ImageCmsProfile(srgb_profile).tobytes()

    variant_img.save(webp_path, format="WEBP", quality=safe_q, icc_profile=srgb_bytes, method=6)
    variant_img.save(jpeg_path, format="JPEG", quality=safe_q, icc_profile=srgb_bytes, optimize=True)

    return {"webp": str(webp_path), "jpeg": str(jpeg_path), "width": actual_w}


def process_image(
    raw_bytes: bytes,
    original_filename: str,
    output_dir: Path,
    originals_dir: Optional[Path] = None,
) -> dict:
    """
    Elabora un'immagine secondo la pipeline completa.
    Restituisce un dict con tutti i metadati da salvare nel DB.
    """
    if not HAS_PIL:
        raise RuntimeError("Pillow non installato. Esegui: pip install Pillow")

    # 1. Verifica formato MIME reale
    mime = detect_mime(raw_bytes)
    if mime not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Formato immagine non supportato o file non valido (MIME: {mime})")

    raw_size = len(raw_bytes)

    # 2. Verifica limite upload grezzo
    if raw_size > settings.upload_max_bytes:
        raise ValueError(
            f"File troppo grande ({raw_size // 1024 // 1024} MB). "
            f"Limite: {settings.upload_max_bytes // 1024 // 1024} MB."
        )

    # 3. Anti decompression bomb — imposta limite PRIMA di aprire
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS

    try:
        img = Image.open(io.BytesIO(raw_bytes))
        # Forza la decodifica completa per verificare subito
        img.verify()
        # Riapri dopo verify (verify() consuma il file)
        img = Image.open(io.BytesIO(raw_bytes))
    except Exception as e:
        raise ValueError(f"Immagine non valida o corrotta: {e}")

    # 4. Applica orientamento EXIF (corregge rotazione)
    img = ImageOps.exif_transpose(img)

    orig_w, orig_h = img.size

    # 5. Converti in RGB (rimuove canale alpha se necessario, gestisce palette)
    if img.mode in ("RGBA", "LA"):
        # Composita su sfondo bianco
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "RGBA":
            background.paste(img, mask=img.split()[3])
        else:
            background.paste(img)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # 6. Rimuovi metadati (GPS e altri) — crea immagine pulita
    clean_img = Image.frombytes("RGB", img.size, img.tobytes())

    # 7. Converti profilo colore in sRGB
    srgb_profile = ImageCms.createProfile("sRGB")
    srgb_bytes_profile = ImageCms.ImageCmsProfile(srgb_profile).tobytes()
    existing_icc = img.info.get("icc_profile")
    if existing_icc:
        try:
            input_profile = ImageCms.ImageCmsProfile(io.BytesIO(existing_icc))
            clean_img = ImageCms.profileToProfile(
                clean_img, input_profile, srgb_profile,
                renderingIntent=ImageCms.Intent.PERCEPTUAL,
            )
        except Exception:
            # Se la conversione fallisce, usa l'immagine pulita con sRGB assegnato
            pass

    # 8. Ridimensiona se necessario (no upscale)
    max_dim = settings.image_max_dimension
    if clean_img.width > max_dim or clean_img.height > max_dim:
        clean_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    # 9. Nome file sicuro e univoco
    base_name = _safe_filename(original_filename)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 10. Salva originale pulito nella directory privata (se richiesto)
    if originals_dir:
        originals_dir.mkdir(parents=True, exist_ok=True)
        orig_path = originals_dir / f"{base_name}_original.jpg"
        clean_img.save(orig_path, format="JPEG", quality=95, icc_profile=srgb_bytes_profile)

    # 11. Genera varianti responsive
    quality = settings.image_quality_webp
    variants = {}
    for w in RESPONSIVE_WIDTHS:
        v = _save_variant(clean_img, w, output_dir, base_name, quality)
        variants[str(v["width"])] = {"webp": v["webp"], "jpeg": v["jpeg"]}

    # Percorso principale (massima risoluzione disponibile)
    main_w = min(clean_img.width, max_dim)
    main_webp = output_dir / f"{base_name}_{main_w}w.webp"
    main_jpeg = output_dir / f"{base_name}_{main_w}w.jpg"

    # 12. Verifica output ≤ 5 MB — riduzione progressiva qualità
    final_q = quality
    while main_webp.exists() and main_webp.stat().st_size > settings.image_max_output_bytes:
        final_q = max(settings.image_quality_min, final_q - 5)
        if final_q == settings.image_quality_min:
            break
        clean_img.save(main_webp, format="WEBP", quality=final_q, icc_profile=srgb_bytes_profile)
        clean_img.save(main_jpeg, format="JPEG", quality=final_q, icc_profile=srgb_bytes_profile, optimize=True)

    # 13. Hash SHA256 dell'output principale
    output_bytes = main_webp.read_bytes() if main_webp.exists() else raw_bytes
    file_hash = _sha256(output_bytes)

    # Percorsi relativi alla root del progetto
    def rel(p: Path) -> str:
        try:
            return str(p.relative_to(settings.project_root)).replace("\\", "/")
        except ValueError:
            return str(p).replace("\\", "/")

    variants_rel = {
        k: {"webp": rel(Path(v["webp"])), "jpeg": rel(Path(v["jpeg"]))}
        for k, v in variants.items()
    }

    return {
        "storedFilename": base_name,
        "mimeType": mime,
        "width": clean_img.width,
        "height": clean_img.height,
        "originalWidth": orig_w,
        "originalHeight": orig_h,
        "fileSizeBytes": main_webp.stat().st_size if main_webp.exists() else 0,
        "originalSizeBytes": raw_size,
        "hashSha256": file_hash,
        "webpPath": rel(main_webp),
        "jpegPath": rel(main_jpeg),
        "variants": json.dumps(variants_rel),
        "wasRescaled": (orig_w > max_dim or orig_h > max_dim),
        "finalQuality": final_q,
    }
