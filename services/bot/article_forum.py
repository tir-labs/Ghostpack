"""Publish public Ghost articles to one explicitly public Discord forum."""
import html
import os
import re
from urllib.parse import urlparse
import discord
from ghost_publish import GhostPublisher

FORUM_ID=int(os.environ.get("DISCORD_ARTICLES_FORUM_ID","0"))
PUBLIC_IDS={int(x) for x in os.environ.get("DISCORD_PUBLIC_FORUM_IDS","").split(",") if x.strip().isdigit()}
def public_forum(forum,guild):
    everyone=guild.default_role
    perms=forum.permissions_for(everyone)
    return forum.id in PUBLIC_IDS and perms.view_channel and perms.read_message_history and perms.send_messages_in_threads
def ghost_url(value):
    base=urlparse(os.environ["GHOST_URL"])
    parsed=urlparse(value)
    if parsed.scheme!="https" or parsed.hostname!=base.hostname or parsed.username or parsed.password:
        raise ValueError("Article URL must belong to configured HTTPS Ghost host")
    return value
def description(post):
    excerpt=html.unescape(re.sub("<[^>]+>"," ",post.get("custom_excerpt") or post.get("excerpt") or ""))
    return excerpt[:900]
async def publish(bot,post,api):
    """Call only after Ghost Admin API confirms the article is published."""
    forum=bot.get_channel(FORUM_ID)
    if not isinstance(forum,discord.ForumChannel) or not public_forum(forum,forum.guild):
        raise ValueError("Article forum is not public or is not allowlisted")
    if post.get("status")!="published":raise ValueError("Article is not published")
    url=ghost_url(post["url"])
    post_id=str(post["id"])
    title=post["title"][:100]
    tags=[tag for tag in forum.available_tags if tag.name.lower() in {t.get("name","").lower() for t in post.get("tags",[])}][:5]
    author_mentions=[]
    # Only IDs explicitly configured by newsroom admins; never guess a Discord user from an email.
    import json
    mapped=json.loads(os.environ.get("GHOST_AUTHOR_DISCORD_IDS","{}"))
    for author in post.get("authors",[]):
        discord_id=str(mapped.get(str(author.get("id")),""))
        if discord_id.isdigit() and forum.guild.get_member(int(discord_id)):
            author_mentions.append(f"<@{discord_id}>")
    embed=discord.Embed(title=post["title"][:256],url=url,description=description(post),color=discord.Color.blurple())
    media=post.get("feature_image")
    if media and urlparse(media).scheme=="https":embed.set_image(url=media)
    if post.get("feature_image_caption"):embed.set_footer(text=re.sub("<[^>]+>"," ",post["feature_image_caption"])[:200])
    body="Read the full article: "+url
    if author_mentions:body+="\nBy "+", ".join(author_mentions)
    # A video URL can be supplied in the article text; Discord decides whether it embeds.
    existing=await api("GET",f"/internal/discussions/articles/{post_id}")
    if existing.get("thread_id"):
        thread=bot.get_channel(int(existing["thread_id"])) or await bot.fetch_channel(int(existing["thread_id"]))
        if thread.parent_id!=forum.id:raise ValueError("Mapped thread is outside public article forum")
        starter=await thread.fetch_message(thread.id)
        if starter.author.id!=bot.user.id:raise ValueError("Forum starter is not bot-owned")
        await starter.edit(content=body,embed=embed,allowed_mentions=discord.AllowedMentions(users=True,roles=False,everyone=False))
        if thread.name!=title or {t.id for t in thread.applied_tags}!={t.id for t in tags}:
            await thread.edit(name=title,applied_tags=tags)
    else:
        created=await forum.create_thread(name=title,content=body,embed=embed,applied_tags=tags,
            allowed_mentions=discord.AllowedMentions(users=True,roles=False,everyone=False))
        thread=created.thread
    await api("PUT","/internal/discussions/articles",{"ghost_post_id":post_id,"forum_id":str(forum.id),
        "thread_id":str(thread.id),"thread_url":f"https://discord.com/channels/{forum.guild.id}/{thread.id}","title":post["title"][:300],
        "excerpt":description(post),"featured_url":media if media and urlparse(media).hostname in ("postdated.org","www.postdated.org") else None,
        "tags":[t.name for t in tags]})
    return thread
async def sync_published(bot,api):
    """Periodic polling avoids requiring a publicly exposed Ghost webhook."""
    if not FORUM_ID:return
    publisher=GhostPublisher()
    result=await publisher.request("GET","posts/?limit=all&filter=status:published&include=authors,tags")
    for post in result.get("posts",[]):
        try:await publish(bot,post,api)
        except Exception as exc:print("Article sync error",post.get("id"),type(exc).__name__,str(exc)[:160])
