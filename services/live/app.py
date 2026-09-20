import os, secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
import store
TOKEN=os.environ.get("LIVE_TOKEN","")
def auth(authorization):
    if not TOKEN or not authorization or not secrets.compare_digest(authorization,"Bearer "+TOKEN):
        raise HTTPException(401,"Unauthorized")
def execute(fn,*args):
    try: return fn(*args)
    except ValueError as exc: raise HTTPException(409,str(exc))
@asynccontextmanager
async def lifespan(app):
    store.init()
    yield
app=FastAPI(title="Ghostpack Live",lifespan=lifespan)
class Event(BaseModel):
    title:str=Field(min_length=1,max_length=300)
    thread_id:str|None=None
class Submission(BaseModel):
    event_id:str
    reporter_id:str
    body:str=Field(min_length=1)
    media:list[dict]=Field(default_factory=list)
class Revision(BaseModel):
    reporter_id:str
    body:str=Field(min_length=1)
class Decision(BaseModel):
    version:int=Field(ge=1)
    editor_id:str
    action:str
    note:str|None=None
class Publication(BaseModel):
    ghost_url:str
@app.get("/health")
def health(): return {"ok":True}
@app.post("/events")
def create(data:Event,authorization:str|None=Header(None)):
    auth(authorization);return execute(store.event,data.title,data.thread_id)
@app.post("/updates")
def submit(data:Submission,authorization:str|None=Header(None)):
    auth(authorization);return execute(store.submit,data.event_id,data.reporter_id,data.body,data.media)
@app.post("/updates/{id}/revise")
def revise(id:str,data:Revision,authorization:str|None=Header(None)):
    auth(authorization);return execute(store.revise,id,data.reporter_id,data.body)
@app.post("/updates/{id}/decision")
def decide(id:str,data:Decision,authorization:str|None=Header(None)):
    auth(authorization);return execute(store.decide,id,data.version,data.editor_id,data.action,data.note)
@app.post("/updates/{id}/published")
def publish(id:str,data:Publication,authorization:str|None=Header(None)):
    auth(authorization);return execute(store.published,id,data.ghost_url)
@app.get("/events/{id}/archive")
def archive(id:str,authorization:str|None=Header(None)):
    auth(authorization);return execute(store.archive,id)
@app.post("/events/{id}/end")
def end(id:str,authorization:str|None=Header(None)):
    auth(authorization);return execute(store.end,id)

@app.get("/threads/{thread_id}/event")
def thread_event(thread_id:str,authorization:str|None=Header(None)):
    auth(authorization)
    event=store.by_thread(thread_id)
    if not event: raise HTTPException(404,"No active event for thread")
    return event

# Public reads are intentionally isolated from authenticated editorial endpoints.
from public import router as public_router
from ghost_events import router as ghost_router
app.include_router(public_router)
app.include_router(ghost_router)
