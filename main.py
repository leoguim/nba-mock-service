from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Literal
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

class NBARequest(BaseModel):
    user_id: str
    session_id: str
    page: str
    zones: list[str]


class ZoneAction(BaseModel):
    zone: str
    action_type: Literal["theme", "segment", "offer"]
    action_value: str
    metadata: dict[str, Any] = {}


class NBAResponse(BaseModel):
    user_id: str
    actions: list[ZoneAction]


# --- Mock data pool per zone ---
# Each zone has curated actions that make sense contextually.
# Falls back to a generic pool for unknown zones.

ZONE_ACTIONS: dict[str, list[dict]] = {
    "hero": [
        {"action_type": "theme",   "action_value": "summer_sale",        "metadata": {"headline": "Up to 30% off", "cta": "Shop Now"}},
        {"action_type": "theme",   "action_value": "new_collection",     "metadata": {"headline": "Just Arrived", "cta": "Explore"}},
        {"action_type": "offer",   "action_value": "free_shipping",      "metadata": {"min_order": 50, "cta": "Get Free Shipping"}},
        {"action_type": "theme",   "action_value": "flash_sale",         "metadata": {"headline": "Today Only", "cta": "Shop the Sale"}},
    ],
    "recommendations": [
        {"action_type": "segment", "action_value": "trending_products",  "metadata": {"algorithm": "collaborative_filter", "count": 8}},
        {"action_type": "segment", "action_value": "recently_viewed",    "metadata": {"algorithm": "session_based", "count": 6}},
        {"action_type": "segment", "action_value": "top_rated",          "metadata": {"algorithm": "rating_based", "count": 8}},
        {"action_type": "offer",   "action_value": "bundle_deal",        "metadata": {"discount": "15%", "applies_to": "recommended_items"}},
    ],
    "categories": [
        {"action_type": "segment", "action_value": "electronics",        "metadata": {"priority": 1, "badge": "Hot"}},
        {"action_type": "segment", "action_value": "fashion",            "metadata": {"priority": 1, "badge": "New"}},
        {"action_type": "theme",   "action_value": "seasonal_categories","metadata": {"season": "spring", "highlight": True}},
        {"action_type": "segment", "action_value": "deals_of_the_day",   "metadata": {"refresh_interval": "24h"}},
    ],
    "loyalty": [
        {"action_type": "segment", "action_value": "gold_tier",          "metadata": {"points": 1500, "next_tier": "platinum", "points_needed": 500}},
        {"action_type": "offer",   "action_value": "double_points",      "metadata": {"valid_until": "2025-06-30", "multiplier": 2}},
        {"action_type": "segment", "action_value": "silver_tier",        "metadata": {"points": 800, "next_tier": "gold", "points_needed": 700}},
        {"action_type": "offer",   "action_value": "points_redemption",  "metadata": {"available_points": 1200, "cta": "Redeem Now"}},
    ],
    "articles": [
        {"action_type": "segment", "action_value": "how_to_guides",      "metadata": {"topic": "styling_tips", "count": 5}},
        {"action_type": "segment", "action_value": "trending_articles",  "metadata": {"topic": "new_arrivals", "count": 4}},
        {"action_type": "theme",   "action_value": "editorial_spotlight","metadata": {"theme": "sustainability", "featured": True}},
        {"action_type": "offer",   "action_value": "newsletter_signup",  "metadata": {"reward": "10% off next order", "cta": "Subscribe"}},
    ],
}

FALLBACK_ACTIONS = [
    {"action_type": "theme",   "action_value": "generic_promo",      "metadata": {"discount": "10%"}},
    {"action_type": "segment", "action_value": "popular_items",      "metadata": {"count": 6}},
    {"action_type": "offer",   "action_value": "10_percent_off",     "metadata": {"code": "SAVE10"}},
]


# --- Endpoint ---

@app.post("/next-best-action", response_model=NBAResponse)
def get_next_best_action(request: NBARequest):
    actions = []
    for zone in request.zones:
        pool = ZONE_ACTIONS.get(zone.lower(), FALLBACK_ACTIONS)
        action = random.choice(pool)
        actions.append(
            ZoneAction(
                zone=zone,
                action_type=action["action_type"],
                action_value=action["action_value"],
                metadata={
                    **action["metadata"],
                    "page": request.page,
                    "trace_id": str(uuid.uuid4()),
                },
            )
        )

    return NBAResponse(
        user_id=request.user_id,
        actions=actions,
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "nba-mock"}
