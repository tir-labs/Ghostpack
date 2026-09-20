"""Authenticated, published-only Discord timeline event ingestion."""
import os
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel,Field
import store
router=APIRouter()
def auth(header):
    from app import auth as require
    require(header)
class Link(BaseModel):
    message_id:str
    author_kind:str="reader"
class Reaction(BaseModel):
    emoji:str=Field(min_length=1,max_length=32)
    count:int=Field(ge=0,le=1000000)
class Reply(BaseModel):
    message_id:str
    parent_message_id:str|None=None
    body:str=Field(min_length=1,max_length=4000)
    channel_id:str
    moderated:bool=False
@router.get("/internal/updates/by-message/{message_id}")
def by_message(message_id:str,authorization:str|None=Header(None)):
    auth(authorization)
    return store.public_message(message_id) or (_ for _ in ()).throw(HTTPException(404,"Published update not found"))
@router.post("/internal/updates/{update_id}/message")
def link(update_id:str,data:Link,authorization:str|None=Header(None)):
    auth(authorization)
    with store.connect() as c:
        u=store.get(c,"updates",update_id)
        if not u or u["state"]!="published":raise HTTPException(409,"Update is not published")
    try:store.link_message(update_id,data.message_id,data.author_kind)
    except ValueError as exc:raise HTTPException(409,str(exc))
    return {"ok":True}
@router.post("/internal/updates/messages/{message_id}/reactions")
def react(message_id:str,data:Reaction,authorization:str|None=Header(None)):
    auth(authorization)
    if not store.public_message(message_id):raise HTTPException(404,"Published update not found")
    try:store.reaction(message_id,data.emoji,data.count)
    except ValueError as exc:raise HTTPException(409,str(exc))
    return {"ok":True}
@router.post("/internal/updates/{update_id}/pin")
def pin(update_id:str,authorization:str|None=Header(None)):
    auth(authorization)
    try:store.pin(update_id)
    except ValueError as exc:raise HTTPException(409,str(exc))
    return {"ok":True}
@router.post("/internal/updates/{update_id}/replies")
def reply(update_id:str,data:Reply,authorization:str|None=Header(None)):
    auth(authorization)
    # No unmoderated message is ever copied into the public timeline.
    if not data.moderated:raise HTTPException(403,"Editorial moderation required")
    allowed=set(filter(None,os.environ.get("DISCORD_PUBLIC_FORUM_IDS","").split(",")))
    if data.channel_id not in allowed:raise HTTPException(403,"Channel not allowlisted")
    raise HTTPException(501,"Reply publication requires a per-thread visibility and moderation implementation")
