import json, os, sqlite3, threading, time, uuid
DB=os.environ.get("LIVE_DB","/data/live.sqlite3")
lock=threading.RLock()
def connect():
    c=sqlite3.connect(DB,timeout=30)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c
def init():
    with lock,connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,title TEXT NOT NULL,thread_id TEXT UNIQUE,ghost_post_id TEXT,status TEXT NOT NULL DEFAULT 'draft',created_at INTEGER NOT NULL,ended_at INTEGER);
        CREATE TABLE IF NOT EXISTS updates(id TEXT PRIMARY KEY,event_id TEXT NOT NULL REFERENCES events(id),reporter_id TEXT NOT NULL,body TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,state TEXT NOT NULL DEFAULT 'pending',media TEXT NOT NULL DEFAULT '[]',ghost_url TEXT,created_at INTEGER NOT NULL,published_at INTEGER);
        CREATE TABLE IF NOT EXISTS decisions(id TEXT PRIMARY KEY,update_id TEXT NOT NULL REFERENCES updates(id),version INTEGER NOT NULL,editor_id TEXT NOT NULL,action TEXT NOT NULL,note TEXT,created_at INTEGER NOT NULL,UNIQUE(update_id,version,action));
        """)
def get(c,table,id):
    r=c.execute(f"SELECT * FROM {table} WHERE id=?",(id,)).fetchone()
    return dict(r) if r else None
def event(title,thread_id=None):
    with lock,connect() as c:
        id=uuid.uuid4().hex
        c.execute("INSERT INTO events(id,title,thread_id,created_at) VALUES(?,?,?,?)",(id,title,thread_id,int(time.time())))
        return get(c,"events",id)
def submit(event_id,reporter_id,body,media=None):
    with lock,connect() as c:
        e=get(c,"events",event_id)
        if not e or e["status"]=="ended": raise ValueError("Event missing or ended")
        id=uuid.uuid4().hex
        c.execute("INSERT INTO updates(id,event_id,reporter_id,body,media,created_at) VALUES(?,?,?,?,?,?)",(id,event_id,reporter_id,body,json.dumps(media or []),int(time.time())))
        return get(c,"updates",id)
def revise(id,reporter_id,body):
    with lock,connect() as c:
        u=get(c,"updates",id)
        if not u or u["reporter_id"]!=reporter_id or u["state"] not in ("pending","held"): raise ValueError("Revision not allowed")
        c.execute("UPDATE updates SET body=?,version=version+1,state='pending' WHERE id=?",(body,id))
        return get(c,"updates",id)
def decide(id,version,editor_id,action,note=None):
    if action not in ("approve","hold"): raise ValueError("Invalid action")
    with lock,connect() as c:
        u=get(c,"updates",id)
        if not u or u["version"]!=version or u["state"]!="pending": raise ValueError("Stale or already reviewed")
        c.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?,?)",(uuid.uuid4().hex,id,version,editor_id,action,note,int(time.time())))
        c.execute("UPDATE updates SET state=? WHERE id=?",("approved" if action=="approve" else "held",id))
        return get(c,"updates",id)
def published(id,url):
    with lock,connect() as c:
        u=get(c,"updates",id)
        if not u or u["state"]!="approved": raise ValueError("Not approved")
        c.execute("UPDATE updates SET state='published',ghost_url=?,published_at=? WHERE id=?",(url,int(time.time()),id))
        return get(c,"updates",id)
def end(id):
    with lock,connect() as c:
        e=get(c,"events",id)
        if not e or e["status"]=="ended": raise ValueError("Event missing or ended")
        c.execute("UPDATE events SET status='ended',ended_at=? WHERE id=?",(int(time.time()),id))
        return archive(id,c)
def archive(id,c=None):
    own=c is None
    if own: c=connect()
    try:
        e=get(c,"events",id)
        if not e: raise ValueError("Event not found")
        updates=[dict(r) for r in c.execute("SELECT * FROM updates WHERE event_id=? ORDER BY created_at,id",(id,))]
        for u in updates:
            u["media"]=json.loads(u["media"])
            u["decisions"]=[dict(r) for r in c.execute("SELECT * FROM decisions WHERE update_id=? ORDER BY created_at,id",(u["id"],))]
        return {"event":e,"updates":updates}
    finally:
        if own: c.close()
