"""Ghost post association is authenticated and separate from public timeline reads."""
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel
import store
router=APIRouter()
class Association(BaseModel):
    ghost_post_id:str
@router.post("/events/{event_id}/ghost")
def associate(event_id:str,data:Association,authorization:str|None=Header(None)):
    from app import auth
    auth(authorization)
    with store.lock,store.connect() as c:
        event=store.get(c,"events",event_id)
        if not event:raise HTTPException(404,"Event not found")
        if event["ghost_post_id"] and event["ghost_post_id"]!=data.ghost_post_id:
            raise HTTPException(409,"Ghost post already associated")
        c.execute("UPDATE events SET ghost_post_id=? WHERE id=?",(data.ghost_post_id,event_id))
        return store.get(c,"events",event_id)
