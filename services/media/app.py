"""Development media API. Place behind a trusted reverse proxy before production."""
import asyncio
import os
import pathlib
import secrets
import subprocess
import tempfile
import uuid
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.responses import FileResponse

app = FastAPI(title="Ghostpack Media")
ROOT = pathlib.Path("/data")
ROOT.mkdir(parents=True, exist_ok=True)
TOKEN = os.environ.get("MEDIA_TOKEN", "")
MAX_BYTES = 2 * 1024**3

def authorize(value: str | None):
    if not TOKEN or not value or not secrets.compare_digest(value, "Bearer " + TOKEN):
        raise HTTPException(401, "Unauthorized")

def run(args: list[str]):
    p = subprocess.run(args, capture_output=True, text=True, timeout=14400)
    if p.returncode:
        raise RuntimeError(p.stderr[-1200:])

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/process")
async def process(file: UploadFile = File(...), source: str = Form("ghost"),
                  authorization: str | None = Header(default=None)):
    authorize(authorization)
    if source not in ("ghost", "live"):
        raise HTTPException(400, "Invalid source")
    name = pathlib.Path(file.filename or "").suffix.lower()
    image = name in (".jpg", ".jpeg", ".png", ".webp", ".heic", ".avif")
    video = name in (".mp4", ".mov", ".mkv", ".webm", ".m4v")
    if not (image or video):
        raise HTTPException(415, "Unsupported file type")
    job = uuid.uuid4().hex
    folder = ROOT / job
    folder.mkdir(mode=0o700)
    original = folder / ("source" + name)
    size = 0
    try:
        with original.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(413, "File exceeds configured maximum")
                out.write(chunk)
        if video and source == "live":
            p = await asyncio.to_thread(subprocess.run,
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(original)],
                capture_output=True, text=True, timeout=30)
            try:
                duration = float(p.stdout.strip())
            except ValueError:
                raise HTTPException(422, "Cannot determine duration")
            if duration > 120:
                raise HTTPException(422, "Live videos must be 120 seconds or shorter")
        output = folder / ("output.avif" if image else "output.webm")
        if image:
            await asyncio.to_thread(run, ["ffmpeg", "-nostdin", "-y", "-i", str(original),
                "-frames:v", "1", "-c:v", "libaom-av1", "-crf", "30",
                "-still-picture", "1", str(output)])
        else:
            logo = os.environ.get("WATERMARK_FILE", "")
            cmd = ["ffmpeg", "-nostdin", "-y", "-i", str(original)]
            if logo and pathlib.Path(logo).is_file():
                cmd += ["-i", logo, "-filter_complex",
                        "[1:v]scale=140:-1[logo];[0:v][logo]overlay=W-w-24:H-h-24[v]",
                        "-map", "[v]", "-map", "0:a?"]
            cmd += ["-c:v", "libsvtav1", "-preset", "8", "-crf", "35",
                    "-c:a", "libopus", "-b:a", "96k", str(output)]
            await asyncio.to_thread(run, cmd)
        return {"id": job, "filename": output.name, "download": f"/files/{job}/{output.name}"}
    except HTTPException:
        raise
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(422, f"Processing failed: {str(exc)[-300:]}")

@app.get("/files/{job}/{filename}")
def download(job: str, filename: str, authorization: str | None = Header(default=None)):
    authorize(authorization)
    if len(job) != 32 or not all(c in "0123456789abcdef" for c in job):
        raise HTTPException(404)
    if filename not in ("output.avif", "output.webm"):
        raise HTTPException(404)
    path = ROOT / job / filename
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, filename=filename)
