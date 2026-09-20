"""GhostLive Discord adapter: initial operational workflow; requires configured channel IDs."""
import asyncio
import os
import discord
import httpx
import monitors
import article_forum
from discord import app_commands

TOKEN=os.environ["DISCORD_TOKEN"]
GUILD=int(os.environ["DISCORD_GUILD_ID"])
MANAGEMENT=int(os.environ["DISCORD_MANAGEMENT_CHANNEL_ID"])
REPORTING=int(os.environ["DISCORD_REPORTING_CHANNEL_ID"])
QUEUE=int(os.environ["DISCORD_QUEUE_CHANNEL_ID"])
EDITOR_ROLE=int(os.environ["EDITOR_ROLE_ID"])
API=os.environ.get("LIVE_API_URL","http://live:8090").rstrip("/")
HEADERS={"Authorization":"Bearer "+os.environ["LIVE_TOKEN"]}
intents=discord.Intents.default()
intents.message_content=True
client=discord.Client(intents=intents)
tree=app_commands.CommandTree(client)
async def event_for_thread(thread_id):
    try:
        return await api("GET",f"/threads/{thread_id}/event")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code==404: return None
        raise
async def api(method,path,payload=None):
    async with httpx.AsyncClient(timeout=30) as http:
        response=await http.request(method,API+path,headers=HEADERS,json=payload)
        response.raise_for_status()
        return response.json()
def editor(member):
    return any(role.id==EDITOR_ROLE for role in getattr(member,"roles",[]))
@tree.command(name="monitor",description="Create a recurring RSSHub monitor",guild=discord.Object(id=GUILD))
@app_commands.describe(interval="Check frequency",feed_url="HTTPS RSSHub feed URL",role="Role to ping for new items")
@app_commands.choices(interval=[app_commands.Choice(name=x,value=x) for x in monitors.INTERVALS])
async def monitor(interaction:discord.Interaction,interval:app_commands.Choice[str],feed_url:str,role:discord.Role):
    target=int(os.environ.get("DISCORD_MONITORS_CHANNEL_ID","0"))
    if not target or interaction.channel_id!=target:
        return await interaction.response.send_message("Create monitors in #monitors.",ephemeral=True)
    if not editor(interaction.user):
        return await interaction.response.send_message("Editor role required to create monitors.",ephemeral=True)
    try: mid=monitors.add(interaction.guild_id,target,interaction.user.id,feed_url,interval.value,[role.id])
    except ValueError as exc:
        return await interaction.response.send_message(str(exc),ephemeral=True)
    await interaction.response.send_message(f"Monitor #{mid} created: [{interval.value}] {feed_url} {role.mention}",allowed_mentions=discord.AllowedMentions.none())

@tree.command(name="live",description="Start a GhostLive reporting event",guild=discord.Object(id=GUILD))
@app_commands.describe(title="Working headline for this event")
async def live(interaction:discord.Interaction,title:str):
    if interaction.channel_id!=MANAGEMENT or not editor(interaction.user):
        return await interaction.response.send_message("Editors must use the management channel.",ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    channel=client.get_channel(REPORTING)
    if not isinstance(channel,discord.TextChannel):
        return await interaction.followup.send("Reporting channel not configured.",ephemeral=True)
    thread=await channel.create_thread(name=title[:90],type=discord.ChannelType.public_thread)
    event=await api("POST","/events",{"title":title,"thread_id":str(thread.id)})
    await thread.send("GhostLive reporting thread. Submissions enter the editor queue; this is not yet a published Ghost article.")
    await interaction.followup.send(f"Event {event['id']} created: {thread.mention}",ephemeral=True)
@tree.command(name="end",description="Close a GhostLive event",guild=discord.Object(id=GUILD))
@app_commands.describe(thread_id="Discord reporting thread ID")
async def end(interaction:discord.Interaction,thread_id:str):
    if interaction.channel_id!=MANAGEMENT or not editor(interaction.user):
        return await interaction.response.send_message("Editors must use the management channel.",ephemeral=True)
    try: thread_number=int(thread_id)
    except ValueError: return await interaction.response.send_message("Invalid thread ID.",ephemeral=True)
    event=await event_for_thread(str(thread_number))
    if not event: return await interaction.response.send_message("No active event for this thread.",ephemeral=True)
    event_id=event["id"]
    await interaction.response.defer(ephemeral=True)
    archive=await api("POST",f"/events/{event_id}/end")
    thread=client.get_channel(thread_number)
    if isinstance(thread,discord.Thread): await thread.edit(archived=True,locked=True)
    await interaction.followup.send(f"Event closed. Private archive available via authenticated API: /events/{event_id}/archive. It contains unpublished submissions; do not share publicly.",ephemeral=True)
class Review(discord.ui.View):
    def __init__(self,update_id,version):
        super().__init__(timeout=None)
        self.update_id=update_id
        self.version=version
    async def decide(self,interaction,action):
        if not editor(interaction.user):
            return await interaction.response.send_message("Editor role required.",ephemeral=True)
        try: result=await api("POST",f"/updates/{self.update_id}/decision",{"version":self.version,"editor_id":str(interaction.user.id),"action":action})
        except httpx.HTTPStatusError:
            return await interaction.response.send_message("This submission is stale or already reviewed.",ephemeral=True)
        for item in self.children: item.disabled=True
        await interaction.response.edit_message(content=f"{action.upper()} by {interaction.user.mention} · update {self.update_id}. Ghost publication is not connected yet.",view=self)
    @discord.ui.button(label="Approve",style=discord.ButtonStyle.success,emoji="✅")
    async def approve(self,interaction:discord.Interaction,button:discord.ui.Button):
        await self.decide(interaction,"approve")
    @discord.ui.button(label="Hold",style=discord.ButtonStyle.secondary,emoji="⚠️")
    async def hold(self,interaction:discord.Interaction,button:discord.ui.Button):
        await self.decide(interaction,"hold")
@client.event
async def on_message(message):
    if message.author.bot or not isinstance(message.channel,discord.Thread): return
    event=await event_for_thread(str(message.channel.id))
    if not event: return
    event_id=event["id"]
    from media_ingest import ingest
    media=[]
    for attachment in message.attachments:
        try:
            media.append(await ingest(attachment,event_id))
        except (httpx.HTTPError,OSError,ValueError) as exc:
            await message.reply("Attachment ingestion failed; this submission was not queued. Contact an editor.")
            print("Private attachment ingest error:",repr(exc))
            return
    if not message.content.strip() and not media: return
    try:
        update=await api("POST","/updates",{"event_id":event_id,"reporter_id":str(message.author.id),"body":message.content.strip() or "[Media submission]","media":media})
        channel=client.get_channel(QUEUE)
        if channel:
            await channel.send(f"Review update {update['id']} from {message.author.mention} in {message.channel.mention}:\n{message.content[:1400]}\nAttachments: {len(media)}",view=Review(update["id"],update["version"]))
        await message.add_reaction("📝")
    except (httpx.HTTPError,discord.HTTPException) as exc:
        print("Submission error:",repr(exc))
async def public_update_message(payload):
    if payload.guild_id!=GUILD or not payload.message_id:return None
    channel=client.get_channel(payload.channel_id)
    if channel is None:
        try:channel=await client.fetch_channel(payload.channel_id)
        except discord.HTTPException:return None
    # Only configured public forums, never staff channels or arbitrary threads.
    if not isinstance(channel,discord.Thread) or channel.parent_id not in article_forum.PUBLIC_IDS:
        return None
    parent=channel.parent or client.get_channel(channel.parent_id)
    if not isinstance(parent,discord.ForumChannel) or not article_forum.public_forum(parent,parent.guild):
        return None
    try:return await api("GET",f"/internal/updates/by-message/{payload.message_id}")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code==404:return None
        raise

@client.event
async def on_raw_reaction_add(payload):
    await sync_reaction(payload,added=True)
@client.event
async def on_raw_reaction_remove(payload):
    await sync_reaction(payload,added=False)
async def sync_reaction(payload,added):
    if payload.user_id==client.user.id:return
    try:
        update=await public_update_message(payload)
        if not update:return
        channel=client.get_channel(payload.channel_id) or await client.fetch_channel(payload.channel_id)
        message=await channel.fetch_message(payload.message_id)
        emoji=str(payload.emoji)
        count=next((r.count for r in message.reactions if str(r.emoji)==emoji),0)
        await api("POST",f"/internal/updates/messages/{payload.message_id}/reactions",{"emoji":emoji,"count":count})
        if added and emoji=="📌":
            member=payload.member or channel.guild.get_member(payload.user_id)
            if member and editor(member):await api("POST",f"/internal/updates/{update['id']}/pin")
    except (discord.HTTPException,httpx.HTTPError,ValueError) as exc:
        print("Public reaction sync error",type(exc).__name__,str(exc)[:160])

@client.event
async def on_ready():
    if not getattr(client,"article_scheduler_started",False):
        client.article_scheduler_started=True
        asyncio.create_task(article_scheduler())
    if not getattr(client,"monitor_scheduler_started",False):
        client.monitor_scheduler_started=True
        asyncio.create_task(monitors.scheduler(client))
    await tree.sync(guild=discord.Object(id=GUILD))
    print("GhostLive bot online:",client.user)
async def article_scheduler():
    await client.wait_until_ready()
    while not client.is_closed():
        try:
            guild=client.get_guild(GUILD)
            if guild and article_forum.FORUM_ID:
                await article_forum.sync_published(client,api)
                snapshot={"guild_id":str(guild.id),"name":guild.name,"icon_url":str(guild.icon.url) if guild.icon else None,
                    "members":guild.member_count,"online":None,"boosts":guild.premium_subscription_count}
                await api("PUT","/internal/discussions/community",snapshot)
        except Exception as exc:print("Article scheduler error",type(exc).__name__,str(exc)[:160])
        await asyncio.sleep(900)
client.run(TOKEN)
