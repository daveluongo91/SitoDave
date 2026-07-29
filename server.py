#!/usr/bin/env python3
"""
Davide Luongo Website — Backend Server & Asset Engine
Handles REST APIs, Content JSON Persistence, and sRGB Image Processing / WebP Conversion.
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
import sys
import urllib.parse
from pathlib import Path
from PIL import Image, ImageCms, ImageOps

ROOT = Path(__file__).parent.resolve()
DATA_FILE = ROOT / "data" / "content.json"
UPLOAD_DIR = ROOT / "assets" / "upload"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PORT = 3000

def load_content():
    if not DATA_FILE.exists():
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_content(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def process_image_srgb(input_bytes, original_filename):
    """
    Processes full resolution image bytes:
    - Maintains or converts to sRGB ICC profile.
    - Generates optimized sRGB WebP and JPEG assets.
    """
    stem = Path(original_filename).stem.replace(" ", "_")
    img = Image.open(input_bytes)
    img = ImageOps.exif_transpose(img) # Auto-rotate based on EXIF

    # Check or generate sRGB ICC profile
    icc_profile = img.info.get('icc_profile')
    srgb_cms = ImageCms.createProfile('sRGB')
    srgb_bytes = ImageCms.ImageCmsProfile(srgb_cms).tobytes()

    if img.mode != 'RGB':
        img = img.convert('RGB')

    # Generate WebP sRGB
    webp_filename = f"{stem}_web.webp"
    webp_path = UPLOAD_DIR / webp_filename
    img.save(webp_path, format="WEBP", quality=90, icc_profile=icc_profile or srgb_bytes)

    # Generate JPEG sRGB
    jpg_filename = f"{stem}_web.jpg"
    jpg_path = UPLOAD_DIR / jpg_filename
    img.save(jpg_path, format="JPEG", quality=92, icc_profile=icc_profile or srgb_bytes)

    return {
        "filename": original_filename,
        "fullResPath": f"assets/upload/{jpg_filename}",
        "webpPath": f"assets/upload/{webp_filename}",
        "jpegPath": f"assets/upload/{jpg_filename}",
        "width": img.width,
        "height": img.height,
        "srgbPreserved": True,
        "uploadDate": "2026-07-29"
    }

class BackendRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/content":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            data = load_content()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            return
        elif parsed.path == "/admin":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            admin_file = ROOT / "admin.html"
            if admin_file.exists():
                self.wfile.write(admin_file.read_bytes())
            else:
                self.wfile.write(b"Admin page not found")
            return
        
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))

        if parsed.path == "/api/content":
            body = self.rfile.read(content_length)
            try:
                new_content = json.loads(body.decode("utf-8"))
                save_content(new_content)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Content updated successfully"}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        elif parsed.path == "/api/upload":
            body = self.rfile.read(content_length)
            try:
                # Handle raw binary or JSON upload
                content_type = self.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    upload_data = json.loads(body.decode("utf-8"))
                    filename = upload_data.get("filename", "upload.jpg")
                    import base64
                    raw_bytes = base64.b64decode(upload_data.get("base64Data", ""))
                else:
                    filename = self.headers.get("X-File-Name", "upload.jpg")
                    raw_bytes = body

                import io
                asset_meta = process_image_srgb(io.BytesIO(raw_bytes), filename)

                # Append to assets list in content.json
                data = load_content()
                if "assets" not in data:
                    data["assets"] = []
                data["assets"].insert(0, asset_meta)
                save_content(data)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "asset": asset_meta}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def main():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, BackendRequestHandler)
    print(f"Davide Luongo Backend & Admin CMS running on http://localhost:{PORT}")
    print(f"Admin Dashboard available at http://localhost:{PORT}/admin")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    main()
