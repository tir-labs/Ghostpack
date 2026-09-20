"""GhostLive Discord adapter: initial operational workflow; requires configured channel IDs."""
import asyncio
import os
import discord
import httpx
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
threads={}
pending={}
async def api(method,path,payload=None):
    async with httpx.AsyncClient(timeout=30) as http:
        response=await http.request(method,API+path,headers=HEADERS,json=payload)
        response.raise_for_status()
        return response.json()
def editor(member):
    return any(role.id==EDITOR_ROLE for role in getattr(member,"roles",[]))
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
    threads[thread.id]=event["id"]
    await thread.send("GhostLive reporting thread. Submissions enter the editor queue; this is not yet a published Ghost article.")
    await interaction.followup.send(f"Event {event['id']} created: {thread.mention}",ephemeral=True)
@tree.command(name="end",description="Close a GhostLive event",guild=discord.Object(id=GUILD))
@app_commands.describe(thread_id="Discord reporting thread ID")
async def end(interaction:discord.Interaction,thread_id:str):
    if interaction.channel_id!=MANAGEMENT or not editor(interaction.user):
        return await interaction.response.send_message("Editors must use the management channel.",ephemeral=True)
    try: thread_number=int(thread_id)
    except ValueError: return await interaction.response.send_message("Invalid thread ID.",ephemeral=True)
    event_id=threads.get(thread_number)
    if not event_id: return await interaction.response.send_message("Unknown thread in this bot session.",ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    archive=await api("POST",f"/events/{event_id}/end")
    thread=client.get_channel(thread_number)
    if isinstance(thread,discord.Thread): await thread.edit(archived=True,locked=True)
    threads.pop(thread_number,None)
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
    event_id=threads.get(message.channel.id)
    if not event_id: return
    media=[{"discord_attachment_id":str(a.id),"filename":a.filename,"url":a.url,"size":a.size} for a in message.attachments]
    if not message.content.strip() and not media: return
    try:
        update=await api("POST","/updates",{"event_id":event_id,"reporter_id":str(message.author.id),"body":message.content.strip() or "[Media submission]","media":media})
        channel=client.get_channel(QUEUE)
        if channel:
            await channel.send(f"Review update {update['id']} from {message.author.mention} in {message.channel.mention}:\n{message.content[:1400]}\nAttachments: {len(media)}",view=Review(update["id"],update["version"]))
        await message.add_reaction("📝")
    except (httpx.HTTPError,discord.HTTPException) as exc:
        print("Submission error:",repr(exc))
@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD))
    print("GhostLive bot online:",client.user)
client.run(TOKEN)
