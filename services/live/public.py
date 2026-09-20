"""Published-only public timeline. Never expose private media paths or unapproved replies."""
import json
from fastapi import APIRouter, HTTPException
import store
router=APIRouter()
@router.get("/public/events/{event_id}")
def published_event(event_id:str):
    with store.connect() as con:
        event=store.get(con,"events",event_id)
        if not event or not event["ghost_post_id"]:
            raise HTTPException(404,"Published event not found")
        updates=[dict(row) for row in con.execute("SELECT id,body,ghost_url,published_at FROM updates WHERE event_id=? AND state='published' ORDER BY published_at,id",(event_id,))]
        meta={row["update_id"]:dict(row) for row in con.execute("SELECT m.* FROM timeline_meta m JOIN updates u ON u.id=m.update_id WHERE u.event_id=? AND u.state='published'",(event_id,))}
        result=[]
        for u in updates:
            m=meta.get(u["id"],{})
            counts=json.loads(m.get("emoji_counts","{}"))
            reactions=sorted(counts.items(),key=lambda x:(0 if x[0]=="⬆️" else 1 if x[0]=="⬇️" else 2,-x[1],x[0]))
            replies=[dict(x) for x in con.execute("SELECT id,parent_message_id,body,created_at FROM timeline_replies WHERE update_id=? ORDER BY created_at,id",(u["id"],))]
            result.append({**u,"author_kind":m.get("author_kind","reader"),"verified":m.get("author_kind")=="staff","contributor_badge":m.get("author_kind")=="contributor","pinned":bool(m.get("pinned_at")),"reactions":reactions,"replies":replies})
        return {"id":event["id"],"title":event["title"],"status":event["status"],"updates":result}
