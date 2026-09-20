"""Public article discussion metadata is allowlisted; staff messages never enter this table."""
import json
import re
import time
from urllib.parse import urlparse
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel,Field
import store

router=APIRouter()
def init():
    with store.lock,store.connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS article_discussions(
          ghost_post_id TEXT PRIMARY KEY, forum_id TEXT NOT NULL,
          thread_id TEXT NOT NULL UNIQUE, thread_url TEXT NOT NULL,
          title TEXT NOT NULL, excerpt TEXT NOT NULL, featured_url TEXT,
          tags_json TEXT NOT NULL DEFAULT '[]', updated_at INTEGER NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS community_snapshot(
          guild_id TEXT PRIMARY KEY, name TEXT NOT NULL, icon_url TEXT,
          members INTEGER, online INTEGER, boosts INTEGER, updated_at INTEGER NOT NULL)""")
def snowflake(value):
    if not re.fullmatch(r"[0-9]{15,22}",value):raise ValueError("Invalid Discord ID")
    return value
def safe_url(value,hosts):
    if value is None:return None
    u=urlparse(value)
    if u.scheme!="https" or not u.hostname or u.username or u.password or u.hostname.lower() not in hosts:
        raise ValueError("URL host not permitted")
    return value
class Article(BaseModel):
    ghost_post_id:str=Field(min_length=1,max_length=128)
    forum_id:str
    thread_id:str
    thread_url:str
    title:str=Field(min_length=1,max_length=300)
    excerpt:str=Field(default="",max_length=1000)
    featured_url:str|None=None
    tags:list[str]=Field(default_factory=list,max_length=10)
class Snapshot(BaseModel):
    guild_id:str
    name:str=Field(min_length=1,max_length=100)
    icon_url:str|None=None
    members:int|None=Field(default=None,ge=0)
    online:int|None=Field(default=None,ge=0)
    boosts:int|None=Field(default=None,ge=0)
def require(authorization):
    from app import auth
    auth(authorization)
@router.put("/internal/discussions/articles")
def upsert_article(data:Article,authorization:str|None=Header(None)):
    require(authorization)
    try:
        forum=snowflake(data.forum_id);thread=snowflake(data.thread_id)
        safe_url(data.thread_url,{"discord.com","www.discord.com"})
        if f"/{thread}" not in data.thread_url:raise ValueError("Thread URL does not match thread ID")
        if data.featured_url:safe_url(data.featured_url,{"postdated.org","www.postdated.org"})
    except ValueError as exc:raise HTTPException(422,str(exc))
    allowed=set(filter(None,__import__("os").environ.get("DISCORD_PUBLIC_FORUM_IDS","").split(",")))
    if forum not in allowed:raise HTTPException(403,"Forum is not publicly allowlisted")
    init()
    with store.lock,store.connect() as db:
        db.execute("""INSERT INTO article_discussions VALUES(?,?,?,?,?,?,?,?,?)
        ON CONFLICT(ghost_post_id) DO UPDATE SET title=excluded.title,excerpt=excluded.excerpt,
        featured_url=excluded.featured_url,tags_json=excluded.tags_json,updated_at=excluded.updated_at""",
        (data.ghost_post_id,forum,thread,data.thread_url,data.title,data.excerpt,data.featured_url,json.dumps(data.tags),int(time.time())))
    return {"ok":True}
@router.put("/internal/discussions/community")
def update_snapshot(data:Snapshot,authorization:str|None=Header(None)):
    require(authorization)
    try:
        snowflake(data.guild_id)
        if data.icon_url:safe_url(data.icon_url,{"cdn.discordapp.com","media.discordapp.net"})
    except ValueError as exc:raise HTTPException(422,str(exc))
    init()
    with store.lock,store.connect() as db:
        db.execute("""INSERT INTO community_snapshot VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(guild_id) DO UPDATE SET name=excluded.name,icon_url=excluded.icon_url,
        members=excluded.members,online=excluded.online,boosts=excluded.boosts,updated_at=excluded.updated_at""",
        (data.guild_id,data.name,data.icon_url,data.members,data.online,data.boosts,int(time.time())))
    return {"ok":True}
@router.get("/public/discussions/articles/{ghost_post_id}")
def article(ghost_post_id:str):
    init()
    with store.connect() as db:
        row=db.execute("SELECT ghost_post_id,thread_url,title,excerpt,featured_url,tags_json FROM article_discussions WHERE ghost_post_id=?",(ghost_post_id,)).fetchone()
        if not row:raise HTTPException(404,"No public discussion")
        data=dict(row);data["tags"]=json.loads(data.pop("tags_json"))
        return data
@router.get("/public/discussions/community/{guild_id}")
def community(guild_id:str):
    init()
    with store.connect() as db:
        row=db.execute("SELECT name,icon_url,members,online,boosts,updated_at FROM community_snapshot WHERE guild_id=?",(guild_id,)).fetchone()
        if not row:raise HTTPException(404,"No public community snapshot")
        return dict(row)

@router.get("/internal/discussions/articles/{ghost_post_id}")
def internal_article(ghost_post_id:str,authorization:str|None=Header(None)):
    require(authorization)
    init()
    with store.connect() as db:
        row=db.execute("SELECT ghost_post_id,forum_id,thread_id,thread_url FROM article_discussions WHERE ghost_post_id=?",(ghost_post_id,)).fetchone()
        return dict(row) if row else {}
