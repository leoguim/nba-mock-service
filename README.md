# Next Best Action — Mock Service

A deployable mock service that returns 3 ranked segment options per zone, influenced by session and context signals.

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
# → http://localhost:8000
```

## Run with Docker

```bash
docker build -t nba-mock .
docker run -p 8000:8000 nba-mock
```

## Deploy options (free tiers)

### Railway
1. Push this folder to a GitHub repo
2. Go to railway.app → New Project → Deploy from GitHub
3. Railway auto-detects the Dockerfile — done

### Render
1. Push to GitHub
2. New Web Service → connect repo
3. Runtime: Docker, port: 8000

### Fly.io
```bash
fly launch   # detects Dockerfile automatically
fly deploy
```

---

## Request

`POST /next-best-action`

| Field | Type | Required | Description |
|---|---|---|---|
| `user_id` | string | yes | Unique user identifier |
| `session_id` | string | yes | Current session identifier |
| `page` | string | yes | Page being personalised e.g. `homepage` |
| `zones` | string[] | yes | Zones to return actions for |
| `timestamp` | ISO 8601 | yes | Request time |
| `session` | object | no | Session signals — see below |
| `context` | object | no | Page context signals — see below |
| `api_version` | string | no | Schema version, default `1.0` |

### `session` object (all optional)

| Field | Type | Description |
|---|---|---|
| `is_new` | boolean | True if first visit this session |
| `page_count` | integer | Pages viewed in current session |
| `referrer` | string | Traffic source URL |
| `utm_source` | string | UTM source parameter |
| `utm_campaign` | string | UTM campaign parameter |

### `context` object (all optional)

| Field | Type | Description |
|---|---|---|
| `time_of_day` | `morning` \| `afternoon` \| `evening` \| `night` | Time of day |
| `day_of_week` | string | e.g. `saturday` |
| `country` | string | ISO country code e.g. `GB` |

### Supported zones

`hero` · `recommendations` · `categories` · `loyalty` · `articles`

Any unknown zone falls back to a generic segment pool.

### Signal logic

The service derives signal tags from the optional fields and uses them to rank the 3 options returned per zone:

| Input | Signal tag |
|---|---|
| `is_new: true` or `page_count <= 1` | `new_user` |
| `is_new: false` or `page_count > 1` | `returning` |
| any `utm_campaign` or `utm_source` | `campaign` |
| referrer contains google / bing / yahoo | `paid_search` |
| referrer contains email / newsletter | `email` |
| `time_of_day: morning` | `morning` |
| `day_of_week: saturday` or `sunday` | `weekend` |

If no session or context is provided the service falls back to generic untagged segments.

---

## Example request

```bash
curl -X POST https://your-deployed-url/next-best-action \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u_123",
    "session_id": "sess_abc",
    "page": "homepage",
    "zones": ["hero", "recommendations", "loyalty"],
    "timestamp": "2026-04-22T09:15:00Z",
    "session": {
      "is_new": true,
      "page_count": 1,
      "referrer": "google.com",
      "utm_source": "google",
      "utm_campaign": "spring_launch"
    },
    "context": {
      "time_of_day": "morning",
      "day_of_week": "wednesday",
      "country": "GB"
    },
    "api_version": "1.0"
  }'
```

## Example response

```json
{
  "interaction_id": "a3f8c2d1-...",
  "user_id": "u_123",
  "page": "homepage",
  "zones": ["hero", "recommendations", "loyalty"],
  "signals_applied": ["campaign", "morning", "new_user", "paid_search"],
  "actions": [
    {
      "zone": "hero",
      "action_type": "segment",
      "options": [
        {
          "rank": 1,
          "action_value": "welcome_visitor",
          "metadata": { "headline": "Welcome!", "cta": "Explore", "trace_id": "..." }
        },
        {
          "rank": 2,
          "action_value": "campaign_hero",
          "metadata": { "headline": "Campaign Feature", "cta": "Shop Now", "trace_id": "..." }
        },
        {
          "rank": 3,
          "action_value": "morning_pick",
          "metadata": { "headline": "Start Your Day", "cta": "See Today's Picks", "trace_id": "..." }
        }
      ]
    },
    {
      "zone": "recommendations",
      "action_type": "segment",
      "options": [
        { "rank": 1, "action_value": "new_arrivals_recs", "metadata": { "algorithm": "recency_based", "count": 8, "trace_id": "..." } },
        { "rank": 2, "action_value": "campaign_picks",    "metadata": { "algorithm": "campaign_curated", "count": 6, "trace_id": "..." } },
        { "rank": 3, "action_value": "trending_products", "metadata": { "algorithm": "collaborative_filter", "count": 8, "trace_id": "..." } }
      ]
    },
    {
      "zone": "loyalty",
      "action_type": "segment",
      "options": [
        { "rank": 1, "action_value": "join_loyalty",    "metadata": { "reward": "200 welcome points", "cta": "Join Now", "trace_id": "..." } },
        { "rank": 2, "action_value": "loyalty_offer",   "metadata": { "cta": "Claim Reward", "trace_id": "..." } },
        { "rank": 3, "action_value": "campaign_loyalty","metadata": { "cta": "Campaign Reward", "trace_id": "..." } }
      ]
    }
  ],
  "request_timestamp": "2026-04-22T09:15:00Z",
  "response_timestamp": "2026-04-22T09:15:00.123Z"
}
```

### Response fields

| Field | Description |
|---|---|
| `interaction_id` | Unique ID for this request — use for tracing and logging |
| `signals_applied` | Signal tags derived from session and context that influenced ranking |
| `actions[].action_type` | Always `segment` |
| `actions[].options` | 3 distinct segment options ranked 1 (best match) to 3 |
| `options[].rank` | 1 = highest signal relevance, 3 = lowest |
| `options[].metadata.trace_id` | Per-option trace identifier |

---

## Swagger UI

Visit `/docs` on your deployed URL for interactive API docs and live testing.
