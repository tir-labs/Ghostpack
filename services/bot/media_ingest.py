"""Private Discord attachment ingestion with bounded streaming and no public CDN references."""
import asyncio
import os
import pathlib
import secrets
import tempfile
import httpx

ROOT=pathlib.Path(os.environ.get("ATTACHMENT_DIR","/data/attachments"))
MAX_BYTES=int(os.environ.get("ATTACHMENT_MAX_BYTES",str(1024**3)))

async def ingest(attachment, event_id:str):
    """Download immediately; caller must store the returned private path securely."""
    if attachment.size>MAX_BYTES: raise ValueError("Attachment exceeds private ingest limit")
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    folder=ROOT/event_id
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    target=folder/secrets.token_hex(24)
    size=0
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30,read=180),follow_redirects=False) as client:
            async with client.stream("GET",attachment.url) as response:
                response.raise_for_status()
                with target.open("xb") as f:
                    os.chmod(target,0o600)
                    async for chunk in response.aiter_bytes(1024*1024):
                        size+=len(chunk)
                        if size>MAX_BYTES: raise ValueError("Attachment exceeds private ingest limit")
                        f.write(chunk)
        return {"discord_attachment_id":str(attachment.id),"filename":attachment.filename,
                "private_path":str(target),"size":size,"status":"ingested"}
    except Exception:
        target.unlink(missing_ok=True)
        raise
