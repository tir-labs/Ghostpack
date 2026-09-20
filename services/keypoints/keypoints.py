"""Opt-in OpenAI-compatible summarization; pass only published update text."""
import os
import httpx
async def generate(title:str,published_updates:list[dict])->dict:
    base=os.environ["MODEL_BASE_URL"].rstrip("/")
    key=os.environ["MODEL_API_KEY"]
    model=os.environ["MODEL_NAME"]
    sources=[{"id":u["id"],"body":u["body"]} for u in published_updates if u.get("state")=="published"]
    if not sources: return {"points":[],"source_ids":[]}
    prompt="Write 3 to 5 concise factual key points grounded ONLY in these published newsroom updates. Do not invent facts. Return JSON object with key 'points' containing an array of strings.\nTitle: "+title+"\nSources: "+__import__("json").dumps(sources)
    async with httpx.AsyncClient(timeout=90) as client:
        r=await client.post(base+"/chat/completions",headers={"Authorization":"Bearer "+key},json={"model":model,"messages":[{"role":"user","content":prompt}],"temperature":0,"response_format":{"type":"json_object"}})
        r.raise_for_status()
        result=r.json()
    import json
    points=json.loads(result["choices"][0]["message"]["content"])["points"]
    if not isinstance(points,list) or not 3<=len(points)<=5 or not all(isinstance(p,str) for p in points):
        raise ValueError("Invalid key points response")
    return {"points":points,"source_ids":[s["id"] for s in sources],"status":"needs_editor_review"}
