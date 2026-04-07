# MediaMaster v2

> Multi-platform social media agent with modular architecture — 7+ platforms support.

**Phase 1** (✅) — Modular architecture foundation  
**Phase 2** (✅) — FastAPI layer + LangGraph workflows

## Architecture

```
src/mediamasterv2/
├── core/
│   ├── base.py           # BasePlatform abstract interface
│   ├── factory.py        # PlatformFactory registry
│   └── config.py         # PlatformConfig (YAML + env override)
├── platforms/
│   ├── postiz_adapter.py  # Postiz API (LinkedIn, Twitter, IG)
│   ├── youtube_connector.py
│   ├── discord_bot.py
│   ├── telegram_bot.py
│   ├── pinterest_connector.py
│   ├── twitch_connector.py
│   └── tiktok_connector.py  # Stub
├── api/
│   ├── main.py           # FastAPI app entry point
│   ├── routes.py         # API endpoints
│   ├── schemas.py        # Pydantic request/response models
│   ├── lifespan.py       # Startup/shutdown lifecycle
│   └── dependencies.py   # DI helpers
└── workflows/
    ├── publish.py        # LangGraph: validate → post → verify
    ├── schedule.py       # LangGraph: validate → timing → schedule
    └── analytics.py      # LangGraph: fetch → aggregate → analyze
```

## Quick Start

```bash
git clone https://github.com/cyrilolivieri/mediamaster-v2
cd mediamaster-v2
pip install -e .

# Run API
uvicorn mediamasterv2.api.main:app --reload --port 8000
```

## Configuration

```yaml
# ~/.mediamaster/config.yaml
global:
  postiz_api_key: your_postiz_api_key
  max_retries: 3

linkedin:
  api_key: your_key
  postiz_url: http://localhost:4000
  workspace_id: your_workspace

youtube:
  client_secrets_path: ~/.config/mediamaster/client_secrets.json
  credentials_path: ~/.config/mediamaster/youtube_credentials.json
```

Or via environment variables: `POSTIZ_API_KEY`, `DISCORD_BOT_TOKEN`, `TELEGRAM_BOT_TOKEN`.

## API Endpoints

### `POST /api/post` — Publish content

```json
{
  "content": "Hello from MediaMaster v2! 🚀",
  "platforms": ["linkedin", "twitter"],
  "media_urls": ["https://example.com/image.jpg"]
}
```

### `POST /api/schedule` — Schedule content

```json
{
  "content": "Scheduled announcement",
  "platforms": ["linkedin"],
  "scheduled_at": "2025-06-01T10:00:00Z"
}
```

### `GET /api/analytics/{platform}` — Fetch analytics

```
GET /api/analytics/linkedin?days=7
```

### `GET /api/health` — Health check all platforms

### `GET /api/platforms` — List available platforms

## LangGraph Workflows

### Publish Workflow
```
validate → select_platforms → post_to_platforms → verify_results → finalize
```

### Schedule Workflow
```
validate → calculate_timing → schedule_on_platforms → confirm
```

### Analytics Workflow
```
validate → fetch_analytics → aggregate_data → analyze_data → generate_report
```

## Usage Example

```python
from mediamasterv2.workflows.publish import run_publish
from mediamasterv2.core.factory import PlatformFactory
from mediamasterv2.api.schemas import PlatformName

# Direct API
result = await run_publish(
    content="Hello world!",
    platforms=["linkedin", "twitter"],
)

# Via Factory
factory = PlatformFactory()
linkedin = factory.create("linkedin", config)
await linkedin.post("Hello", networks=["linkedin"])
```

## Testing

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=mediamasterv2 --cov-report=term-missing
```

## Supported Platforms

| Platform | Status | Capabilities |
|----------|--------|-------------|
| LinkedIn | ✅ Active | post, schedule, analytics |
| Twitter/X | ✅ Active | post, schedule, analytics |
| Instagram | ✅ Active | post, schedule |
| YouTube | ✅ Active | upload, schedule |
| Discord | 🔧 Ready | post, engage |
| Telegram | 🔧 Ready | post |
| Pinterest | 🔧 Ready | post |
| Twitch | 🔧 Ready | stream |
| TikTok | ⏳ Stub | pending API approval |

## Testing the API

```bash
# Health check
curl http://localhost:8000/api/health

# List platforms
curl http://localhost:8000/api/platforms

# Post (requires Postiz running)
curl -X POST http://localhost:8000/api/post \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello!", "platforms": ["linkedin"]}'
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Lint
ruff check src/

# Type check
mypy src/
```

## Roadmap

- **Phase 3** — Webhook handling, rate limiting, retry queues
- **Phase 4** — Content calendar UI, A/B testing, advanced analytics
