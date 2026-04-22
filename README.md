# Next Best Action — Mock Service

A deployable mock service that returns personalised segment options per zone, driven by session and context signals. Each zone category has its own selection rules and option count.

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
| `zones` | ZoneRequest[] | yes | Zones to return actions for — see below |
| `timestamp` | ISO 8601 | yes | Request time |
| `session` | object | no | Session signals — see below |
| `context` | object | no | Page context signals — see below |
| `api_version` | string | no | Schema version, default `1.0` |

### `zones` — array of zone objects

Each zone has a `name` (your identifier for that slot on the page) and a `category` (which pool and rules to apply).

| Field | Type | Description |
|---|---|---|
| `name` | string | Zone identifier e.g. `hero_banner`, `cat_grid` |
| `category` | string | One of: `hero`, `categories`, `recommendations`, `loyalty`, `articles` |

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

---

## Zone categories — rules and segments

| Category | Options returned | Selection | Segments |
|---|---|---|---|
| `hero` | 1 | Random | VIP Platinum, Young Mom, Young Professional, Lapsed Customer |
| `categories` | 3 | Random ranked | outerwear, knitwear, accessories, dresses, shoes, basics |
| `recommendations` | 1 | Random | outerwear, knitwear, accessories, dresses, shoes, basics |
| `loyalty` | 1 | Signal-ranked | gold_tier, silver_tier, join_loyalty, points_balance, tier_progress, loyalty_offer, weekend_bonus, campaign_loyalty |
| `articles` | 3 | Signal-ranked | how_to_guides, trending_articles, editorial_spotlight, newsletter_teaser, campaign_editorial, morning_reads, weekend_reads, returning_faves |

### Signal logic

Session and context fields are converted into signal tags that influence ranking for signal-ranked zones:

| Input | Signal tag |
|---|---|
| `is_new: true` or `page_count <= 1` | `new_user` |
| `is_new: false` or `page_count > 1` | `returning` |
| any `utm_campaign` or `utm_source` | `campaign` |
| referrer contains google / bing / yahoo | `paid_search` |
| referrer contains email / newsletter | `email` |
| `time_of_day: morning` | `morning` |
| `day_of_week: saturday` or `sunday` | `weekend` |

`hero` and `categories` ignore signals — their selection is always random.

---

## Example request

```bash
curl -X POST https://your-deployed-url/next-best-action \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u_123",
    "session_id": "sess_abc",
    "page": "homepage",
    "zones": [
      { "name": "hero_banner", "category": "hero" },
      { "name": "cat_grid",    "category": "categories" },
      { "name": "recs_row",    "category": "recommendations" },
      { "name": "loyalty_bar", "category": "loyalty" },
      { "name": "blog_strip",  "category": "articles" }
    ],
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
  "zones": ["hero_banner", "cat_grid", "recs_row", "loyalty_bar", "blog_strip"],
  "actions": [
    {
      "zone": "hero_banner",
      "category": "hero",
      "action_type": "segment",
      "options": [
        { "rank": 1, "action_value": "Young Professional", "metadata": { "trace_id": "..." } }
      ]
    },
    {
      "zone": "cat_grid",
      "category": "categories",
      "action_type": "segment",
      "options": [
        { "rank": 1, "action_value": "outerwear",    "metadata": { "trace_id": "..." } },
        { "rank": 2, "action_value": "accessories",  "metadata": { "trace_id": "..." } },
        { "rank": 3, "action_value": "dresses",      "metadata": { "trace_id": "..." } }
      ]
    },
    {
      "zone": "recs_row",
      "category": "recommendations",
      "action_type": "segment",
      "options": [
        { "rank": 1, "action_value": "new_arrivals_recs", "metadata": { "count": 8, "trace_id": "..." } }
      ]
    },
    {
      "zone": "loyalty_bar",
      "category": "loyalty",
      "action_type": "segment",
      "options": [
        { "rank": 1, "action_value": "join_loyalty", "metadata": { "reward": "200 welcome points", "cta": "Join Now", "trace_id": "..." } }
      ]
    },
    {
      "zone": "blog_strip",
      "category": "articles",
      "action_type": "segment",
      "options": [
        { "rank": 1, "action_value": "newsletter_teaser",  "metadata": { "topic": "weekly_picks",  "count": 3, "trace_id": "..." } },
        { "rank": 2, "action_value": "campaign_editorial", "metadata": { "topic": "campaign_theme","count": 4, "trace_id": "..." } },
        { "rank": 3, "action_value": "morning_reads",      "metadata": { "topic": "daily_picks",   "count": 3, "trace_id": "..." } }
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
| `actions[].zone` | Zone name as provided in the request |
| `actions[].category` | Zone category used to select the pool and rules |
| `actions[].action_type` | Always `segment` |
| `actions[].options` | 1 or 3 segment options depending on category — see zone rules table |
| `options[].rank` | 1 = best match or first random pick, ascending |
| `options[].metadata.count` | Number of items to display (recommendations only) |
| `options[].metadata.trace_id` | Per-option trace identifier |

---

## Swagger UI

Visit `/docs` on your deployed URL for interactive API docs and live testing.
