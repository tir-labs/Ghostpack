"""Ghost Admin API publishing adapter. Requires an existing Ghost post and explicit editor approval."""
import base64
import hashlib
import hmac
import html
import json
import os
import time
import httpx

def token(key):
    kid,secret=key.split(":",1)
    encode=lambda x:base64.urlsafe_b64encode(json.dumps(x,separators=(",",":")).encode()).rstrip(b"=")
    header=encode({"alg":"HS256","typ":"JWT","kid":kid})
    now=int(time.time())
    payload=encode({"iat":now,"exp":now+300,"aud":"/admin/"})
    unsigned=header+b"."+payload
    signature=base64.urlsafe_b64encode(hmac.new(bytes.fromhex(secret),unsigned,hashlib.sha256).digest()).rstrip(b"=")
    return (unsigned+b"."+signature).decode()

class GhostPublisher:
    def __init__(self,base_url=None,key=None):
        self.base=(base_url or os.environ["GHOST_URL"]).rstrip("/")
        self.key=key or os.environ["GHOST_ADMIN_API_KEY"]
    async def request(self,method,path,body=None):
        async with httpx.AsyncClient(timeout=45) as client:
            response=await client.request(method,self.base+"/ghost/api/admin/"+path,
                headers={"Authorization":"Ghost "+token(self.key),"Accept-Version":"v5.0"},
                json=body)
            response.raise_for_status()
            return response.json()
    async def create_draft(self,title,description=""):
        body={"posts":[{"title":title,"status":"draft","lexical":json.dumps({"root":{"children":[{"type":"paragraph","children":[{"type":"extended-text","text":description,"version":1}],"version":1}],"direction":None,"format":"","indent":0,"type":"root","version":1}})}]}
        result=await self.request("POST","posts/",body)
        return result["posts"][0]
    async def get_post(self,post_id):
        result=await self.request("GET",f"posts/{post_id}/")
        return result["posts"][0]
    async def append_approved_text(self,post_id,text):
        """Add an approved paragraph without replacing existing Ghost content. Uses HTML source conversion."""
        post=await self.get_post(post_id)
        existing=post.get("html") or ""
        addition="<p>"+html.escape(text).replace("\n","<br>")+"</p>"
        payload={"posts":[{"html":existing+addition,"updated_at":post["updated_at"]}]}
        result=await self.request("PUT",f"posts/{post_id}/?source=html",payload)
        return result["posts"][0]
