from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Optional, Literal
from datetime import datetime, timezone
import random
import uuid

app = FastAPI(title="Next Best Action - Mock Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---

class SessionContext(BaseModel):
    is_new: Optional[bool] = None
    page_count: Optional[int] = 1
    referrer: Optional[str] = None
    utm_source: Optional[str] = None
    utm_campaign: Optional[str] = None


class PageContext(BaseModel):
    time_of_day: Optional[Literal["morning", "afternoon", "evening", "night"]] = None
    day_of_week: Optional[str] = None
    country: Optional[str] = None


class NBARequest(BaseModel):
    user_id: str
    session_id: str
    page: str
    zones: list[str]
    timestamp: datetime
    session: Optional[SessionContext] = None
    context: Optional[PageContext] = None
    api_version: Optional[str] = "1.0"


class SegmentOption(BaseModel):
    action_value: str
    rank: int                        # 1 = highest signal match, 2, 3
    metadata: dict[str, Any] = {}


class ZoneAction(BaseModel):
    zone: str
    action_type: Literal["segment"] = "segment"
    options: list[SegmentOption]     # always 3 distinct options


class NBAResponse(BaseModel):
    interaction_id: str
    user_id: str
    page: str
    zones: list[str]
    actions: list[ZoneAction]
    signals_applied: list[str]
    request_timestamp: datetime
    response_timestamp: datetime


# --- Segment pools per zone ---
# All entries are action_type: segment.
# Tags drive signal-aware scoring; untagged entries are always eligible.

ZONE_SEGMENTS: dict[str, list[dict]] = {
    "hero": [
        {"action_value": "welcome_visitor",    "metadata": {"headline": "Welcome!",          "cta": "Explore"},           "tags": ["new_user"]},
        {"action_value": "first_time_offer",   "metadata": {"headline": "First Visit Deal",  "cta": "Claim Offer"},       "tags": ["new_user"]},
        {"action_value": "returning_picks",    "metadata": {"headline": "Welcome Back",      "cta": "See Your Picks"},    "tags": ["returning"]},
        {"action_value": "campaign_hero",      "metadata": {"headline": "Campaign Feature",  "cta": "Shop Now"},          "tags": ["campaign"]},
        {"action_value": "summer_sale",        "metadata": {"headline": "Up to 30% Off",     "cta": "Shop the Sale"},     "tags": []},
        {"action_value": "new_collection",     "metadata": {"headline": "Just Arrived",      "cta": "Explore"},           "tags": []},
        {"action_value": "weekend_deals",      "metadata": {"headline": "Weekend Offers",    "cta": "Shop Deals"},        "tags": ["weekend"]},
        {"action_value": "morning_pick",       "metadata": {"headline": "Start Your Day",    "cta": "See Today's Picks"}, "tags": ["morning"]},
        {"action_value": "trending_now",       "metadata": {"headline": "Trending Today",    "cta": "See What's Hot"},    "tags": []},
        {"action_value": "paid_search_offer",  "metadata": {"headline": "Exclusive Deal",    "cta": "Claim Now"},         "tags": ["paid_search"]},
    ],
    "recommendations": [
        {"action_value": "trending_products",  "metadata": {"algorithm": "collaborative_filter", "count": 8}, "tags": []},
        {"action_value": "recently_viewed",    "metadata": {"algorithm": "session_based",         "count": 6}, "tags": ["returning"]},
        {"action_value": "top_rated",          "metadata": {"algorithm": "rating_based",          "count": 8}, "tags": []},
        {"action_value": "new_arrivals_recs",  "metadata": {"algorithm": "recency_based",         "count": 8}, "tags": ["new_user"]},
        {"action_value": "campaign_picks",     "metadata": {"algorithm": "campaign_curated",      "count": 6}, "tags": ["campaign"]},
        {"action_value": "bestsellers",        "metadata": {"algorithm": "sales_rank",            "count": 8}, "tags": []},
        {"action_value": "morning_picks",      "metadata": {"algorithm": "time_based",            "count": 6}, "tags": ["morning"]},
        {"action_value": "weekend_specials",   "metadata": {"algorithm": "promo_based",           "count": 6}, "tags": ["weekend"]},
    ],
    "categories": [
        {"action_value": "electronics",        "metadata": {"priority": 1, "badge": "Hot"},      "tags": []},
        {"action_value": "fashion",            "metadata": {"priority": 1, "badge": "New"},      "tags": []},
        {"action_value": "home_living",        "metadata": {"priority": 2, "badge": ""},         "tags": []},
        {"action_value": "beauty",             "metadata": {"priority": 2, "badge": ""},         "tags": []},
        {"action_value": "deals_of_the_day",  "metadata": {"refresh_interval": "24h"},          "tags": ["weekend"]},
        {"action_value": "campaign_category",  "metadata": {"priority": 1, "badge": "Featured"},"tags": ["campaign"]},
        {"action_value": "new_arrivals_cats",  "metadata": {"priority": 1, "badge": "New"},      "tags": ["new_user"]},
        {"action_value": "seasonal",           "metadata": {"priority": 2, "badge": "Season"},   "tags": []},
    ],
    "loyalty": [
        {"action_value": "gold_tier",          "metadata": {"points": 1500, "next_tier": "platinum", "points_needed": 500}, "tags": ["returning"]},
        {"action_value": "silver_tier",        "metadata": {"points": 800,  "next_tier": "gold",     "points_needed": 700}, "tags": ["returning"]},
        {"action_value": "join_loyalty",       "metadata": {"reward": "200 welcome points", "cta": "Join Now"},            "tags": ["new_user"]},
        {"action_value": "points_balance",     "metadata": {"available_points": 1200, "cta": "View Balance"},             "tags": ["returning"]},
        {"action_value": "tier_progress",      "metadata": {"cta": "See Progress"},                                       "tags": ["returning"]},
        {"action_value": "loyalty_offer",      "metadata": {"cta": "Claim Reward"},                                       "tags": []},
        {"action_value": "weekend_bonus",      "metadata": {"multiplier": 2, "cta": "Earn Double"},                       "tags": ["weekend"]},
        {"action_value": "campaign_loyalty",   "metadata": {"cta": "Campaign Reward"},                                    "tags": ["campaign"]},
    ],
    "articles": [
        {"action_value": "how_to_guides",      "metadata": {"topic": "styling_tips",   "count": 5}, "tags": []},
        {"action_value": "trending_articles",  "metadata": {"topic": "new_arrivals",   "count": 4}, "tags": []},
        {"action_value": "editorial_spotlight","metadata": {"topic": "sustainability",  "count": 3}, "tags": []},
        {"action_value": "newsletter_teaser",  "metadata": {"topic": "weekly_picks",   "count": 3}, "tags": ["new_user"]},
        {"action_value": "campaign_editorial", "metadata": {"topic": "campaign_theme", "count": 4}, "tags": ["campaign"]},
        {"action_value": "morning_reads",      "metadata": {"topic": "daily_picks",    "count": 3}, "tags": ["morning"]},
        {"action_value": "weekend_reads",      "metadata": {"topic": "weekend_picks",  "count": 4}, "tags": ["weekend"]},
        {"action_value": "returning_faves",    "metadata": {"topic": "your_interests", "count": 4}, "tags": ["returning"]},
    ],
}

FALLBACK_SEGMENTS = [
    {"action_value": "popular_items",    "metadata": {"count": 6}, "tags": []},
    {"action_value": "trending_today",   "metadata": {"count": 6}, "tags": []},
    {"action_value": "editors_picks",    "metadata": {"count": 6}, "tags": []},
    {"action_value": "new_arrivals",     "metadata": {"count": 6}, "tags": []},
]


# --- Signal resolution ---

def resolve_signals(request: NBARequest) -> set[str]:
    signals: set[str] = set()
    s = request.session
    c = request.context

    if s:
        if s.is_new is True or (s.page_count is not None and s.page_count <= 1):
            signals.add("new_user")
        elif s.is_new is False or (s.page_count is not None and s.page_count > 1):
            signals.add("returning")
        if s.utm_campaign or s.utm_source:
            signals.add("campaign")
        if s.referrer:
            ref = s.referrer.lower()
            if any(x in ref for x in ["google", "bing", "yahoo"]):
                signals.add("paid_search")
            elif any(x in ref for x in ["email", "newsletter"]):
                signals.add("email")

    if c:
        if c.time_of_day == "morning":
            signals.add("morning")
        if c.day_of_week and c.day_of_week.lower() in ["saturday", "sunday"]:
            signals.add("weekend")

    return signals


# --- Option selection ---

def pick_three_options(pool: list[dict], signals: set[str]) -> list[dict]:
    """
    Score every segment in the pool by signal match count.
    Split into signal-matched and unmatched buckets, then assemble
    3 distinct options ranked by relevance:
      - slot 1: best signal-matched candidate (or random if none)
      - slots 2-3: filled from remaining pool without repetition
    Always returns exactly 3 distinct options.
    """
    # Score and shuffle within each score group for variety
    scored = sorted(
        [(len(set(a.get("tags", [])) & signals), a) for a in pool],
        key=lambda x: x[0],
        reverse=True,
    )

    # Deduplicate while preserving order
    seen: set[str] = set()
    ranked: list[dict] = []
    for _, action in scored:
        if action["action_value"] not in seen:
            seen.add(action["action_value"])
            ranked.append(action)

    # Ensure we always have 3 — pad with fallback if pool is tiny
    while len(ranked) < 3:
        for fb in FALLBACK_SEGMENTS:
            if fb["action_value"] not in seen:
                seen.add(fb["action_value"])
                ranked.append(fb)
            if len(ranked) == 3:
                break

    # Pick slot 1 as best match; shuffle slots 2-3 from the rest for variety
    top = ranked[0]
    rest = ranked[1:]
    random.shuffle(rest)
    selected = [top] + rest[:2]

    return selected


# --- Endpoint ---

@app.post("/next-best-action", response_model=NBAResponse)
def get_next_best_action(request: NBARequest):
    signals = resolve_signals(request)
    actions = []

    for zone in request.zones:
        pool    = ZONE_SEGMENTS.get(zone.lower(), FALLBACK_SEGMENTS)
        options = pick_three_options(pool, signals)

        zone_options = [
            SegmentOption(
                action_value=opt["action_value"],
                rank=rank,
                metadata={
                    **opt["metadata"],
                    "trace_id": str(uuid.uuid4()),
                },
            )
            for rank, opt in enumerate(options, start=1)
        ]

        actions.append(ZoneAction(zone=zone, options=zone_options))

    return NBAResponse(
        interaction_id=str(uuid.uuid4()),
        user_id=request.user_id,
        page=request.page,
        zones=request.zones,
        actions=actions,
        signals_applied=sorted(signals) if signals else ["none"],
        request_timestamp=request.timestamp,
        response_timestamp=datetime.now(timezone.utc),
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "nba-mock"}
