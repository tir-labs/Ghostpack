"""Read-only published timeline: never expose pending, held or approved-but-unpublished content."""
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
        updates=[dict(row) for row in con.execute(
            "SELECT id,body,ghost_url,published_at,media FROM updates WHERE event_id=? AND state='published' ORDER BY published_at,id",
            (event_id,))]
        # Raw media can include private filesystem paths and Discord URLs. Never return it.
        return {"id":event["id"],"title":event["title"],"status":event["status"],
                "updates":[{"id":u["id"],"body":u["body"],"ghost_url":u["ghost_url"],
                            "published_at":u["published_at"]} for u in updates]}
