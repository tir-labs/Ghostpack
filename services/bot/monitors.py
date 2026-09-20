"""Durable RSS monitor scheduling and daily reports; no third-party cron service."""
import asyncio
import datetime as dt
import io
import ipaddress
import json
import os
import re
import socket
import sqlite3
import urllib.parse
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

import discord
import httpx

DB=os.environ.get("BOT_DB","/data/bot.sqlite3")
EASTERN=ZoneInfo("America/New_York")
INTERVALS={"5M":5,"10M":10,"15M":15,"30M":30,"60M":60,"2H":120,"3H":180,"6H":360,"8H":480,"12H":720,"18H":1080,"24H":1440,"48H":2880,"82H":4920}
def now(): return dt.datetime.now(dt.timezone.utc)
def stamp(value): return value.isoformat()
def connect():
    os.makedirs(os.path.dirname(os.path.abspath(DB)),exist_ok=True)
    db=sqlite3.connect(DB,timeout=30)
    db.row_factory=sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS monitors (id INTEGER PRIMARY KEY, guild_id TEXT NOT NULL, channel_id TEXT NOT NULL, creator_id TEXT NOT NULL, feed_url TEXT NOT NULL, interval TEXT NOT NULL, role_ids TEXT NOT NULL, created TEXT NOT NULL, next_check TEXT NOT NULL, review_due TEXT NOT NULL, last_review TEXT, active INTEGER NOT NULL DEFAULT 1, last_item TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS seen (monitor_id INTEGER NOT NULL, item_id TEXT NOT NULL, PRIMARY KEY(monitor_id,item_id))")
    db.execute("CREATE TABLE IF NOT EXISTS daily_reports (day TEXT PRIMARY KEY)")
    db.commit()
    return db
def valid_url(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None,443):
        raise ValueError("Feed must be an HTTPS URL on port 443 without credentials")
    host=parsed.hostname.lower().rstrip(".")
    if host not in ("rsstown.com",) and not host.endswith(".rsstown.com"):
        raise ValueError("Feeds must use the newsroom RSSHub host rsstown.com")
    return url
def add(guild,channel,creator,url,interval,roles):
    valid_url(url)
    if interval not in INTERVALS: raise ValueError("Invalid interval")
    if not roles or len(roles)>10 or not all(str(x).isdigit() for x in roles): raise ValueError("Select 1–10 Discord roles")
    t=now()
    with connect() as db:
        cursor=db.execute("INSERT INTO monitors(guild_id,channel_id,creator_id,feed_url,interval,role_ids,created,next_check,review_due) VALUES(?,?,?,?,?,?,?,?,?)",(str(guild),str(channel),str(creator),url,interval,json.dumps([str(x) for x in roles]),stamp(t),stamp(t),stamp(t+dt.timedelta(days=10))))
        return cursor.lastrowid
def active():
    with connect() as db: return [dict(r) for r in db.execute("SELECT * FROM monitors WHERE active=1 ORDER BY id")]
def stop(mid):
    with connect() as db: db.execute("UPDATE monitors SET active=0 WHERE id=?",(mid,))
def renew(mid):
    with connect() as db: db.execute("UPDATE monitors SET review_due=?,last_review=? WHERE id=? AND active=1",(stamp(now()+dt.timedelta(days=10)),stamp(now()),mid))
def due():
    with connect() as db: return [dict(r) for r in db.execute("SELECT * FROM monitors WHERE active=1 AND next_check<=?",(stamp(now()),))]
def reserve(mid,interval):
    with connect() as db: db.execute("UPDATE monitors SET next_check=? WHERE id=?",(stamp(now()+dt.timedelta(minutes=INTERVALS[interval])),mid))
def new_items(mid,items):
    fresh=[]
    with connect() as db:
        for key,title,link in items:
            if db.execute("INSERT OR IGNORE INTO seen(monitor_id,item_id) VALUES(?,?)",(mid,key)).rowcount: fresh.append((title,link))
    return fresh
def parse_feed(xml):
    root=ET.fromstring(xml)
    found=[]
    for item in list(root.findall(".//item"))+list(root.findall(".//{http://www.w3.org/2005/Atom}entry")):
        def field(*names):
            for name in names:
                element=item.find(name)
                if element is not None:
                    value=element.get("href") if name.endswith("}link") else element.text
                    if value: return value.strip()
            return ""
        title=field("title","{http://www.w3.org/2005/Atom}title")[:250]
        link=field("link","{http://www.w3.org/2005/Atom}link")
        key=field("guid","id","{http://www.w3.org/2005/Atom}id") or link
        if key and link.startswith("https://"): found.append((key[:1000],title or "New feed item",link))
    return found[:100]
class Review(discord.ui.View):
    def __init__(self,monitor_id,creator_id):
        super().__init__(timeout=None)
        self.monitor_id=monitor_id;self.creator_id=creator_id
        for action,label,style in (("yes","🟢 Yes",discord.ButtonStyle.success),("no","🔴 No",discord.ButtonStyle.danger)):
            button=discord.ui.Button(label=label,style=style,custom_id=f"monitor:{monitor_id}:{action}")
            button.callback=self.callback_for(action)
            self.add_item(button)
    def callback_for(self,action):
        async def callback(interaction):
            if interaction.user.id!=self.creator_id:
                return await interaction.response.send_message("Only the monitor creator can answer.",ephemeral=True)
            if action=="yes": renew(self.monitor_id)
            else: stop(self.monitor_id)
            for item in self.children:item.disabled=True
            await interaction.response.edit_message(content=f"Monitor #{self.monitor_id}: {'renewed for 10 days' if action=='yes' else 'stopped'} by {interaction.user.mention}.",embed=None,view=self)
        return callback
async def fetch(url):
    valid_url(url)
    # RSSHub must be pinned to a publicly routable address; never follow redirects.
    addresses=await asyncio.to_thread(socket.getaddrinfo,"rsstown.com",443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("RSSHub resolved to a non-public address")
    async with httpx.AsyncClient(timeout=20,follow_redirects=False,trust_env=False) as client:
        response=await client.get(url)
        response.raise_for_status()
        if len(response.content)>2_000_000: raise ValueError("Feed too large")
        return parse_feed(response.content)
async def tick(bot):
    for m in due():
        reserve(m["id"],m["interval"])
        try:
            items=new_items(m["id"],await fetch(m["feed_url"]))
            channel=bot.get_channel(int(m["channel_id"]))
            if channel and items:
                roles=" ".join(f"<@&{r}>" for r in json.loads(m["role_ids"]))
                for title,link in items[:10]:
                    await channel.send(f"{roles}\n**{discord.utils.escape_markdown(title)}**\n{link}",allowed_mentions=discord.AllowedMentions(roles=True,users=False,everyone=False))
        except Exception as exc: print("Monitor check failed",m["id"],type(exc).__name__,str(exc)[:180])
    for m in active():
        if m["review_due"]>stamp(now()):continue
        channel=bot.get_channel(int(m["channel_id"]))
        if not channel:continue
        await channel.send(content=f"<@{m['creator_id']}>",embed=discord.Embed(title=f"Monitor #{m['id']}",description="Do you still need this monitor?"),view=Review(m["id"],int(m["creator_id"])),allowed_mentions=discord.AllowedMentions(users=True,roles=False,everyone=False))
        with connect() as db: db.execute("UPDATE monitors SET review_due=? WHERE id=?",(stamp(now()+dt.timedelta(days=1)),m["id"]))
async def daily(bot):
    local=now().astimezone(EASTERN)
    if local.hour!=19:return
    day=local.date().isoformat()
    with connect() as db:
        if db.execute("SELECT 1 FROM daily_reports WHERE day=?",(day,)).fetchone():return
    channel_id=os.environ.get("DISCORD_MONITORS_CHANNEL_ID")
    channel=bot.get_channel(int(channel_id)) if channel_id else None
    if not channel:return
    rows=active()
    report="Active RSS monitors — "+day+" (America/New_York)\n\n"
    for m in rows:report+=f"#{m['id']} [{m['interval']}] {m['feed_url']} creator={m['creator_id']} roles={','.join(json.loads(m['role_ids']))}\n"
    if not rows:report+="No active feeds.\n"
    data=report.encode()
    await channel.send(file=discord.File(io.BytesIO(data),filename=f"active-monitors-{day}.txt"))
    with connect() as db:db.execute("INSERT OR IGNORE INTO daily_reports(day) VALUES(?)",(day,))
async def scheduler(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            await tick(bot)
            await daily(bot)
        except Exception as exc:print("Monitor scheduler error",repr(exc))
        await asyncio.sleep(60)
