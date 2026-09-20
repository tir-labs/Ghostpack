"""Ghost Admin API upload client. Video endpoint is installation-dependent and opt-in."""
import base64
import hashlib
import hmac
import json
import mimetypes
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

def admin_token(key: str) -> str:
    key_id, secret = key.split(":", 1)
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": key_id}
    payload = {"iat": now, "exp": now + 300, "aud": "/admin/"}
    encode = lambda obj: base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode()).rstrip(b"=")
    unsigned = encode(header) + b"." + encode(payload)
    signature = hmac.new(bytes.fromhex(secret), unsigned, hashlib.sha256).digest()
    return (unsigned + b"." + base64.urlsafe_b64encode(signature).rstrip(b"=")).decode()

def upload_image(path: Path, *, ghost_url: str, admin_key: str, timeout: int = 120) -> str:
    """Upload an AVIF image via Ghost Admin images endpoint; returns Ghost URL."""
    if path.suffix.lower() != ".avif":
        raise ValueError("Expected AVIF")
    boundary = "ghostpack" + os.urandom(12).hex()
    mime = "image/avif"
    data = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\nContent-Type: {mime}\r\n\r\n".encode()
            + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode())
    url = ghost_url.rstrip("/") + "/ghost/api/admin/images/upload/"
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Authorization": "Ghost " + admin_token(admin_key),
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Accept-Version": "v5.0",
    })
    with urllib.request.urlopen(req, timeout=timeout) as response:
        result = json.load(response)
    images = result.get("images", [])
    if not images or not isinstance(images[0].get("url"), str):
        raise ValueError("Ghost returned no image URL")
    return images[0]["url"]
