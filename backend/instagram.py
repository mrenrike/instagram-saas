# backend/instagram.py
"""
Instagram Graph API data collection.
Fetches last 60 posts (no stories) with insights.
All timestamps converted to BRT (UTC-3).
"""
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional

BRT = timezone(timedelta(hours=-3))
BASE_URL = "https://graph.instagram.com/v21.0"
MEDIA_FIELDS = "id,like_count,comments_count,media_type,timestamp,caption,permalink"
PHOTO_METRICS = "impressions,reach,saved,shares"
VIDEO_METRICS = "impressions,reach,saved,shares,video_views"


class TokenExpiredError(Exception):
    pass


class GraphAPIError(Exception):
    pass


async def fetch_posts(user_id: str, access_token: str, limit: int = 60) -> list[dict]:
    """Fetch up to `limit` posts (no stories) with insights. Returns list of post dicts."""
    posts = []
    url = f"{BASE_URL}/{user_id}/media"
    params = {"fields": MEDIA_FIELDS, "access_token": access_token, "limit": 50}

    async with httpx.AsyncClient(timeout=30) as client:
        while len(posts) < limit:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                err = resp.json().get("error", {})
                if err.get("code") == 190:
                    raise TokenExpiredError("Instagram token expired")
                raise GraphAPIError(f"Graph API error: {err}")

            data = resp.json()
            for item in data.get("data", []):
                if item.get("media_type") == "STORY":
                    continue
                if len(posts) >= limit:
                    break
                # Fetch insights
                media_id = item["id"]
                media_type = item.get("media_type", "IMAGE")
                metrics = VIDEO_METRICS if media_type in ("VIDEO", "REEL") else PHOTO_METRICS
                ins_resp = await client.get(
                    f"{BASE_URL}/{media_id}/insights",
                    params={"metric": metrics, "access_token": access_token},
                )
                insights = {}
                if ins_resp.status_code == 200:
                    for m in ins_resp.json().get("data", []):
                        insights[m["name"]] = m.get("values", [{}])[0].get("value", 0)

                # Convert timestamp to BRT
                raw_ts = item.get("timestamp", "")
                dt_brt = None
                if raw_ts:
                    dt_utc = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                    dt_brt = dt_utc.astimezone(BRT)

                posts.append({
                    "id": media_id,
                    "media_type": media_type,
                    "timestamp_brt": dt_brt.isoformat() if dt_brt else "",
                    "hour_brt": dt_brt.hour if dt_brt else None,
                    "weekday_brt": dt_brt.weekday() if dt_brt else None,  # 0=Mon
                    "caption": item.get("caption", ""),
                    "permalink": item.get("permalink", ""),
                    "like_count": item.get("like_count", 0),
                    "comments_count": item.get("comments_count", 0),
                    **insights,
                })

            next_url = data.get("paging", {}).get("next")
            if not next_url:
                break
            url = next_url
            params = {}

    return posts


async def fetch_user_info(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{BASE_URL}/me",
            params={"fields": "id,username,followers_count,media_count,account_type",
                    "access_token": access_token},
        )
    if resp.status_code != 200:
        raise GraphAPIError("Failed to fetch user info")
    return resp.json()
