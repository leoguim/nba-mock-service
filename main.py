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


class ZoneRequest(BaseModel):
    name: str
    category: str   # e.g. "hero", "recommendations", "categories", "loyalty", "articles"


class NBARequest(BaseModel):
    user_id: str
    session_id: str
    page: str
    zones: list[ZoneRequest]
    timestamp: datetime
    session: Optional[SessionContext] = None
    context: Optional[PageContext] = None
    api_version: Optional[str] = "1.0"


class SegmentOption(BaseModel):
    action_value: str
    rank: int
    metadata: dict[str, Any] = {}


class ZoneAction(BaseModel):
    zone: str
    category: str
    action_type: Literal["segment"] = "segment"
    options: list[SegmentOption]


class NBAResponse(BaseModel):
    interaction_id: str
    user_id: str
    page: str
    zones: list[str]
    actions: list[ZoneAction]
    signals_applied: list[str]
    request_timestamp: datetime
    response_timestamp: datetime


# ---------------------------------------------------------------------------
# Segment pools
# ---------------------------------------------------------------------------

# hero — 4 fixed customer segments, return 1 randomly
HERO_SEGMENTS = [
    "VIP Platinum",
    "Young Mom",
    "Young Professional",
    "Lapsed Customer",
]

# categories — 6 fashion categories, return 3 randomly ranked
CATEGORY_OPTIONS = [
    "outerwear",
    "knitwear",
    "accessories",
    "dresses",
    "shoes",
    "basics",
]

# recommendations — same pool, return 1 (signal-ranked)
RECOMMENDATION_SEGMENTS = [
    {"action_value": "trending_products",  "metadata": {"count": 8}, "tags": []},
    {"action_value": "recently_viewed",    "metadata": {"count": 6}, "tags": ["returning"]},
    {"action_value": "top_rated",          "metadata": {"count": 8}, "tags": []},
    {"action_value": "new_arrivals_recs",  "metadata": {"count": 8}, "tags": ["new_user"]},
    {"action_value": "campaign_picks",     "metadata": {"count": 6}, "tags": ["campaign"]},
    {"action_value": "bestsellers",        "metadata": {"count": 8}, "tags": []},
    {"action_value": "morning_picks",      "metadata": {"count": 6}, "tags": ["morning"]},
    {"action_value": "weekend_specials",   "metadata": {"count": 6}, "tags": ["weekend"]},
]

# loyalty — 3 signal-ranked options
LOYALTY_SEGMENTS = [
    {"action_value": "gold_tier",        "metadata": {"points": 1500, "next_tier": "platinum", "points_needed": 500}, "tags": ["returning"]},
    {"action_value": "silver_tier",      "metadata": {"points": 800,  "next_tier": "gold",     "points_needed": 700}, "tags": ["returning"]},
    {"action_value": "join_loyalty",     "metadata": {"reward": "200 welcome points", "cta": "Join Now"},            "tags": ["new_user"]},
    {"action_value": "points_balance",   "metadata": {"available_points": 1200, "cta": "View Balance"},             "tags": ["returning"]},
    {"action_value": "tier_progress",    "metadata": {"cta": "See Progress"},                                       "tags": ["returning"]},
    {"action_value": "loyalty_offer",    "metadata": {"cta": "Claim Reward"},                                       "tags": []},
    {"action_value": "weekend_bonus",    "metadata": {"multiplier": 2, "cta": "Earn Double"},                       "tags": ["weekend"]},
    {"action_value": "campaign_loyalty", "metadata": {"cta": "Campaign Reward"},                                    "tags": ["campaign"]},
]

# articles — 3 signal-ranked options
ARTICLE_SEGMENTS = [
    {"action_value": "how_to_guides",      "metadata": {"topic": "styling_tips",   "count": 5}, "tags": []},
    {"action_value": "trending_articles",  "metadata": {"topic": "new_arrivals",   "count": 4}, "tags": []},
    {"action_value": "editorial_spotlight","metadata": {"topic": "sustainability",  "count": 3}, "tags": []},
    {"action_value": "newsletter_teaser",  "metadata": {"topic": "weekly_picks",   "count": 3}, "tags": ["new_user"]},
    {"action_value": "campaign_editorial", "metadata": {"topic": "campaign_theme", "count": 4}, "tags": ["campaign"]},
    {"action_value": "morning_reads",      "metadata": {"topic": "daily_picks",    "count": 3}, "tags": ["morning"]},
    {"action_value": "weekend_reads",      "metadata": {"topic": "weekend_picks",  "count": 4}, "tags": ["weekend"]},
    {"action_value": "returning_faves",    "metadata": {"topic": "your_interests", "count": 4}, "tags": ["returning"]},
]

FALLBACK_SEGMENTS = [
    {"action_value": "popular_items",  "metadata": {"count": 6}, "tags": []},
    {"action_value": "trending_today", "metadata": {"count": 6}, "tags": []},
    {"action_value": "editors_picks",  "metadata": {"count": 6}, "tags": []},
]


# ---------------------------------------------------------------------------
# Signal resolution
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Selection helpers
# ---------------------------------------------------------------------------

def pick_one_signal(pool: list[dict], signals: set[str]) -> dict:
    """Return 1 option — highest signal score wins, ties broken randomly."""
    scored = sorted(
        [(len(set(a.get("tags", [])) & signals), a) for a in pool],
        key=lambda x: x[0],
        reverse=True,
    )
    max_score = scored[0][0]
    candidates = [a for s, a in scored if s == max_score]
    return random.choice(candidates)


def pick_n_signal(pool: list[dict], signals: set[str], n: int) -> list[dict]:
    """Return n distinct options, best signal match first, rest shuffled."""
    scored = sorted(
        [(len(set(a.get("tags", [])) & signals), a) for a in pool],
        key=lambda x: x[0],
        reverse=True,
    )
    seen: set[str] = set()
    ranked: list[dict] = []
    for _, action in scored:
        if action["action_value"] not in seen:
            seen.add(action["action_value"])
            ranked.append(action)

    while len(ranked) < n:
        for fb in FALLBACK_SEGMENTS:
            if fb["action_value"] not in seen:
                seen.add(fb["action_value"])
                ranked.append(fb)
            if len(ranked) == n:
                break

    top  = ranked[0]
    rest = ranked[1:]
    random.shuffle(rest)
    return [top] + rest[:n - 1]


# ---------------------------------------------------------------------------
# Zone builders
# ---------------------------------------------------------------------------

def build_hero(signals: set[str]) -> list[SegmentOption]:
    """1 customer segment chosen randomly from the 4 fixed segments."""
    segment = random.choice(HERO_SEGMENTS)
    return [SegmentOption(
        action_value=segment,
        rank=1,
        metadata={"trace_id": str(uuid.uuid4())},
    )]


def build_categories(signals: set[str]) -> list[SegmentOption]:
    """3 randomly ranked fashion categories from the fixed list of 6."""
    selected = random.sample(CATEGORY_OPTIONS, 3)
    return [
        SegmentOption(
            action_value=cat,
            rank=rank,
            metadata={"trace_id": str(uuid.uuid4())},
        )
        for rank, cat in enumerate(selected, start=1)
    ]


def build_recommendations(signals: set[str]) -> list[SegmentOption]:
    """1 recommendation segment — best signal match wins."""
    opt = pick_one_signal(RECOMMENDATION_SEGMENTS, signals)
    return [SegmentOption(
        action_value=opt["action_value"],
        rank=1,
        metadata={"count": opt["metadata"]["count"], "trace_id": str(uuid.uuid4())},
    )]


def build_loyalty(signals: set[str]) -> list[SegmentOption]:
    """3 signal-ranked loyalty segments."""
    opts = pick_n_signal(LOYALTY_SEGMENTS, signals, 3)
    return [
        SegmentOption(
            action_value=opt["action_value"],
            rank=rank,
            metadata={**opt["metadata"], "trace_id": str(uuid.uuid4())},
        )
        for rank, opt in enumerate(opts, start=1)
    ]


def build_articles(signals: set[str]) -> list[SegmentOption]:
    """3 signal-ranked article segments."""
    opts = pick_n_signal(ARTICLE_SEGMENTS, signals, 3)
    return [
        SegmentOption(
            action_value=opt["action_value"],
            rank=rank,
            metadata={**opt["metadata"], "trace_id": str(uuid.uuid4())},
        )
        for rank, opt in enumerate(opts, start=1)
    ]


ZONE_BUILDERS = {
    "hero":            build_hero,
    "categories":      build_categories,
    "recommendations": build_recommendations,
    "loyalty":         build_loyalty,
    "articles":        build_articles,
}


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@app.post("/next-best-action", response_model=NBAResponse)
def get_next_best_action(request: NBARequest):
    signals = resolve_signals(request)
    actions = []

    for zone_req in request.zones:
        category = zone_req.category.lower()
        builder  = ZONE_BUILDERS.get(category)

        if builder:
            options = builder(signals)
        else:
            # Unknown category — fall back to 3 generic segments
            opts = pick_n_signal(FALLBACK_SEGMENTS, signals, 3)
            options = [
                SegmentOption(
                    action_value=opt["action_value"],
                    rank=rank,
                    metadata={**opt["metadata"], "trace_id": str(uuid.uuid4())},
                )
                for rank, opt in enumerate(opts, start=1)
            ]

        actions.append(ZoneAction(
            zone=zone_req.name,
            category=zone_req.category,
            options=options,
        ))

    return NBAResponse(
        interaction_id=str(uuid.uuid4()),
        user_id=request.user_id,
        page=request.page,
        zones=[z.name for z in request.zones],
        actions=actions,
        signals_applied=sorted(signals) if signals else ["none"],
        request_timestamp=request.timestamp,
        response_timestamp=datetime.now(timezone.utc),
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "nba-mock"}
