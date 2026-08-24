# backend/analyzer.py
"""
Calculates engagement metrics from post list.
Generates matplotlib charts as base64-encoded PNGs.
"""
import base64
import io
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

FORMAT_LABEL = {
    "REEL": "Reels",
    "IMAGE": "Foto",
    "CAROUSEL_ALBUM": "Carrossel",
    "VIDEO": "Vídeo",
}
WEEKDAYS_PT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def engagement(post: dict) -> int:
    return (post.get("like_count", 0) + post.get("comments_count", 0)
            + post.get("saved", 0) + post.get("shares", 0))


def calc_metrics(posts: list[dict]) -> dict:
    if not posts:
        return {}

    by_format: dict[str, list] = defaultdict(list)
    for p in posts:
        fmt = p.get("media_type", "IMAGE")
        by_format[fmt].append(p)

    format_stats = {}
    for fmt, fps in by_format.items():
        engs = [engagement(p) for p in fps]
        format_stats[FORMAT_LABEL.get(fmt, fmt)] = {
            "count": len(fps),
            "avg_engagement": round(sum(engs) / len(fps), 1),
            "max_engagement": max(engs),
            "total_reach": sum(p.get("reach", 0) for p in fps),
            "total_impressions": sum(p.get("impressions", 0) for p in fps),
        }

    # Best hours (BRT)
    hour_eng: dict[int, list] = defaultdict(list)
    for p in posts:
        if p.get("hour_brt") is not None:
            hour_eng[p["hour_brt"]].append(engagement(p))
    best_hours = sorted(
        hour_eng.keys(),
        key=lambda h: sum(hour_eng[h]) / len(hour_eng[h]),
        reverse=True,
    )[:3]

    # Best weekdays
    day_eng: dict[int, list] = defaultdict(list)
    for p in posts:
        if p.get("weekday_brt") is not None:
            day_eng[p["weekday_brt"]].append(engagement(p))
    best_days = sorted(
        day_eng.keys(),
        key=lambda d: sum(day_eng[d]) / len(day_eng[d]),
        reverse=True,
    )[:3]

    # Top 5 posts
    top5 = sorted(posts, key=engagement, reverse=True)[:5]

    return {
        "total_posts": len(posts),
        "format_stats": format_stats,
        "best_hours_brt": best_hours,
        "best_days": [WEEKDAYS_PT[d] for d in best_days],
        "top5_posts": [
            {
                "permalink": p.get("permalink", ""),
                "media_type": FORMAT_LABEL.get(p.get("media_type", ""), p.get("media_type", "")),
                "engagement": engagement(p),
                "timestamp_brt": p.get("timestamp_brt", ""),
                "caption_preview": (p.get("caption", "") or "")[:120],
            }
            for p in top5
        ],
        "avg_engagement_all": round(
            sum(engagement(p) for p in posts) / len(posts), 1
        ),
    }


def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def make_charts(metrics: dict) -> dict[str, str]:
    charts = {}

    # Engagement by format
    if metrics.get("format_stats"):
        fmt_stats = metrics["format_stats"]
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar(list(fmt_stats.keys()), [v["avg_engagement"] for v in fmt_stats.values()], color="#6366f1")
        ax.set_title("Engajamento médio por formato")
        ax.set_ylabel("Engajamento")
        charts["format_chart"] = _fig_to_b64(fig)

    return charts
