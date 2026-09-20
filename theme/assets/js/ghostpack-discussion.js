/* Ghostpack article discussion panel: insert in Ghost theme post.hbs with
   <div class="ghostpack-discussion" data-post-id="{{id}}" data-guild-id="YOUR_GUILD_ID"
        data-api-base="https://ghostbot.postdated.org"></div>
   <script defer src="{{asset "js/ghostpack-discussion.js"}}"></script>
   The API must be publicly reverse-proxied only for /public/discussions/.
   No staff-only messages or private API credentials are used here. */
(() => {
  const discordMark = '<svg viewBox="0 0 127.14 96.36" width="22" height="18" aria-hidden="true" fill="currentColor"><path d="M104.4 8.58A101.7 101.7 0 0 0 79.1 0a72.1 72.1 0 0 0-3.24 6.7 94.2 94.2 0 0 0-28.57 0A72.1 72.1 0 0 0 44.05 0 101.7 101.7 0 0 0 18.75 8.58C2.76 32.26-1.58 55.36.59 78.13a102.3 102.3 0 0 0 31.05 18.23 77.6 77.6 0 0 0 6.65-10.82 66.4 66.4 0 0 1-10.48-5.04c.88-.64 1.74-1.3 2.57-1.98 20.2 9.5 42.1 9.5 62.06 0 .84.68 1.7 1.34 2.58 1.98a66.4 66.4 0 0 1-10.49 5.04 77.6 77.6 0 0 0 6.65 10.82 102.3 102.3 0 0 0 31.05-18.23c2.55-26.39-4.35-49.27-18.16-69.55ZM42.45 65.3c-6.06 0-11.04-5.52-11.04-12.3s4.87-12.31 11.04-12.31c6.21 0 11.14 5.57 11.04 12.31 0 6.78-4.88 12.3-11.04 12.3Zm42.24 0c-6.06 0-11.04-5.52-11.04-12.3s4.87-12.31 11.04-12.31c6.21 0 11.14 5.57 11.04 12.31 0 6.78-4.88 12.3-11.04 12.3Z"/></svg>';
  const css = '.gp-panel{border:1px solid #ddd;border-radius:14px;padding:20px;margin:28px 0;font:inherit}.gp-head{display:flex;align-items:center;gap:12px}.gp-icon{width:52px;height:52px;border-radius:14px;object-fit:cover}.gp-tags{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}.gp-tag{font-size:12px;border-radius:16px;padding:4px 9px;background:#eee;color:#333}.gp-stats{display:flex;gap:20px;flex-wrap:wrap;margin:14px 0}.gp-stats span{font-size:13px}.gp-button{display:flex;align-items:center;justify-content:center;gap:10px;background:#5865F2;color:#fff!important;text-decoration:none!important;padding:13px;border-radius:9px;font-weight:700}.gp-button:focus-visible{outline:3px solid #222;outline-offset:3px}';
  const style = document.createElement('style');style.textContent=css;document.head.append(style);
  const el=(tag,cls,text)=>{const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node;};
  async function get(url){const res=await fetch(url,{credentials:'omit'});if(!res.ok)throw new Error('Not available');return res.json();}
  for(const root of document.querySelectorAll('.ghostpack-discussion')){
    const id=root.dataset.postId,guild=root.dataset.guildId,base=root.dataset.apiBase;
    if(!id||!guild||!base||!/^https:\/\//.test(base))continue;
    Promise.all([get(base+'/public/discussions/articles/'+encodeURIComponent(id)),get(base+'/public/discussions/community/'+encodeURIComponent(guild))])
      .then(([article,community])=>{
        const target=new URL(article.thread_url);
        if(target.protocol!=='https:'||!['discord.com','www.discord.com'].includes(target.hostname))return;
        const panel=el('section','gp-panel');panel.setAttribute('aria-label','Discuss this article on Discord');
        const head=el('div','gp-head');
        if(community.icon_url){const icon=el('img','gp-icon');icon.src=community.icon_url;icon.alt='Discord server icon';icon.loading='lazy';head.append(icon);}
        head.append(el('strong','',community.name));panel.append(head);
        const tags=el('div','gp-tags');for(const tag of article.tags||[])tags.append(el('span','gp-tag','#'+tag));panel.append(tags);
        const stats=el('div','gp-stats');
        for(const [label,value] of [['Members',community.members],['Online',community.online],['Boosts',community.boosts]])stats.append(el('span','',label+': '+(value===null||value===undefined?'Unavailable':Number(value).toLocaleString())));
        panel.append(stats);
        const link=el('a','gp-button');link.href=target.href;link.target='_blank';link.rel='noopener noreferrer';link.innerHTML=discordMark;
        link.append(document.createTextNode('Join the discussion on Discord'));panel.append(link);
        root.replaceChildren(panel);
      }).catch(()=>{root.replaceChildren();});
  }
})();
