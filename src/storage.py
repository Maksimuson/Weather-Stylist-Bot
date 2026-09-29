import os
import json
import aiohttp

URL = os.getenv("UPSTASH_REDIS_REST_URL") or os.getenv("KV_REST_API_URL")
TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN") or os.getenv("KV_REST_API_TOKEN")

_local: dict[int, dict] = {}


async def _cmd(*args):
    async with aiohttp.ClientSession() as s:
        async with s.post(
            URL, headers={"Authorization": f"Bearer {TOKEN}"}, json=list(args)
        ) as r:
            return (await r.json()).get("result")


async def get_user(uid: int) -> dict:
    if not URL:
        return _local.get(uid, {})
    raw = await _cmd("GET", f"user:{uid}")
    return json.loads(raw) if raw else {}


async def set_user(uid: int, data: dict):
    if not URL:
        _local[uid] = data
        return
    await _cmd("SET", f"user:{uid}", json.dumps(data))