# MediaMaster v2

> Multi-platform social media agent with modular architecture — 7+ platforms support.

**Phase 1** focuses on building the foundation: `BasePlatform` interface, `PlatformFactory`, Postiz adapter, and YouTube connector.

## Architecture

```
platforms/
├── base.py              # Abstract BasePlatform interface
├── postiz_adapter.py    # Postiz API wrapper (LinkedIn, Twitter, IG)
├── youtube_connector.py # YouTube Data API v3 + youtube-upload
├── discord_bot.py       # Discord.py bot
├── telegram_bot.py       # python-telegram-bot
├── pinterest_connector.py # Pinterest SDK
├── twitch_connector.py  # twitchAPI
└── tiktok_connector.py  # TikTok (stub — pending API approval)
```

## Quick Start

### Installation

```bash
# Clone
git clone https://github.com/cyrilolivieri/mediamaster-v2
cd mediamaster-v2

# Install dependencies
pip install poetry && poetry install

# Or with pip
pip install -e .
```

### Configuration

```yaml
# ~/.mediamaster/config.yaml
global:
  postiz_api_key: your_postiz_api_key
  max_retries: 3

linkedin:
  api_key: your_linkedin_api_key
  postiz_url: http://localhost:4000
  workspace_id: your_workspace_id

twitter:
  api_key: your_twitter_api_key
  api_secret: your_twitter_secret
  access_token: your_access_token
  access_secret: your_access_secret

youtube:
  client_secrets_path: ~/.config/mediamaster/client_secrets.json
  credentials_path: ~/.config/mediamaster/youtube_credentials.json
  channel_id: your_channel_id
```

Or via environment variables:
```bash
export POSTIZ_API_KEY=your_key
export DISCORD_BOT_TOKEN=your_token
export TELEGRAM_BOT_TOKEN=your_token
```

### Usage

```python
from mediamasterv2.core import load_config, PlatformFactory

# Load config
config = load_config()

# Create a platform instance
factory = PlatformFactory()
linkedin = factory.create("linkedin", config)

# Post to LinkedIn via Postiz
result = await linkedin.post(
    "Hello from MediaMaster v2! 🚀",
    networks=["linkedin"],
    media_urls=["https://example.com/image.jpg"],
)
print(f"Posted: {result.url}")

# Create YouTube connector
youtube = factory.create("youtube", config)
result = await youtube.post(
    "/path/to/video.mp4",
    title="My Video",
    description="Uploaded via MediaMaster!",
    tags=["python", "automation"],
    privacy_status="public",
)

# Create all registered platforms
all_platforms = factory.create_all(config)
```

### Using the Postiz Adapter

Postiz is an open-source social media scheduling tool. The adapter supports:

- **LinkedIn** — posts, images, scheduling
- **Twitter/X** — posts, threads, scheduling
- **Instagram** — posts, reels, scheduling
- **YouTube** — video upload, scheduling

```python
from mediamasterv2.platforms import PostizAdapter

adapter = PostizAdapter({
    "api_key": "your_postiz_key",
    "postiz_url": "http://localhost:4000",
    "workspace_id": "your_workspace",
})

# Post to multiple networks at once
result = await adapter.post(
    "Cross-posting is easy!",
    networks=["linkedin", "twitter", "instagram"],
)

# Schedule for later
from datetime import datetime, timedelta
scheduled = datetime.utcnow() + timedelta(hours=2)
await adapter.schedule(
    "Scheduled content",
    scheduled_at=scheduled,
    networks=["twitter", "linkedin"],
)
```

## Testing

```bash
# Run all tests
poetry run pytest

# With coverage
poetry run pytest --cov=mediamasterv2 --cov-report=term-missing

# Integration tests (require Postiz running)
poetry run pytest tests/integration/
```

## Supported Platforms

| Platform | Status | Capabilities |
|----------|--------|-------------|
| LinkedIn | ✅ Active (Postiz) | post, schedule, analytics |
| Twitter/X | ✅ Active (Postiz) | post, schedule, analytics |
| Instagram | ✅ Active (Postiz) | post, reels, schedule |
| YouTube | ✅ Active | upload, schedule, analytics |
| Discord | 🔧 Ready | post, engage |
| Telegram | 🔧 Ready | post |
| Pinterest | 🔧 Ready | post |
| Twitch | 🔧 Ready | stream |
| TikTok | ⏳ Stub | pending API approval |

## Development

```bash
# Install pre-commit hooks
poetry run pre-commit install

# Lint
poetry run ruff check src/

# Type check
poetry run mypy src/
```

## Roadmap

- **Phase 2** — LangGraph orchestration, FastAPI layer, webhook handling
- **Phase 3** — Full TikTok, Twitch implementations, advanced analytics
- **Phase 4** — Rate limiting, A/B testing, content calendar UI

## License

MIT
