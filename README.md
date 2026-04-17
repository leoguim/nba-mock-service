# Next Best Action — Mock Service

A deployable dummy service that returns realistic fake NBA responses per zone, shaped around `user_type`.

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

## Example request

```bash
curl -X POST https://your-deployed-url/next-best-action \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u_123",
    "user_type": "premium",
    "session_id": "sess_abc",
    "zones": ["homepage_banner", "sidebar", "checkout"]
  }'
```

## Example response

```json
{
  "user_id": "u_123",
  "session_id": "sess_abc",
  "actions": [
    {
      "zone": "homepage_banner",
      "action_type": "theme",
      "action_value": "black_friday_vip",
      "metadata": { "discount": "25%", "badge": "VIP", "trace_id": "a1b2..." }
    },
    {
      "zone": "sidebar",
      "action_type": "offer",
      "action_value": "free_shipping",
      "metadata": { "min_order": 0, "trace_id": "c3d4..." }
    },
    {
      "zone": "checkout",
      "action_type": "segment",
      "action_value": "loyalty_gold",
      "metadata": { "tier": "gold", "points": 1500, "trace_id": "e5f6..." }
    }
  ]
}
```

## Supported user_type values

| user_type  | Action pool                                      |
|------------|--------------------------------------------------|
| `premium`  | VIP themes, loyalty segments, free shipping      |
| `standard` | Seasonal themes, trending segments, discount codes |
| `guest`    | Welcome offers, signup bonuses, bestsellers      |

Any unknown `user_type` falls back to the `standard` pool.

## Swagger UI

Visit `/docs` on your deployed URL for interactive API docs.
# nba-mock-service
# nba-mock-service
