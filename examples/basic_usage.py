"""Example usage of MediaMaster v2."""

import asyncio
from datetime import datetime, timedelta

from mediamasterv2.core import load_config, PlatformFactory
from mediamasterv2.platforms.postiz_adapter import PostizAdapter


async def main():
    # Load configuration from YAML or environment
    config = load_config()

    # Option 1: Use the factory
    factory = PlatformFactory()

    # Create individual platform instances
    linkedin = factory.create("linkedin", config)
    twitter = factory.create("twitter", config)
    youtube = factory.create("youtube", config)

    # Option 2: Direct adapter instantiation
    postiz = PostizAdapter({
        "api_key": config.global_settings.postiz_api_key,
        "postiz_url": config.linkedin.postiz_url,
        "workspace_id": config.linkedin.workspace_id,
    })

    # --- Post to LinkedIn via Postiz ---
    print("Posting to LinkedIn...")
    result = await linkedin.post(
        "Excited to announce MediaMaster v2! 🚀\n\n"
        "Multi-platform social media management is now easier than ever.",
        networks=["linkedin"],
        media_urls=["https://example.com/announcement.jpg"],
    )
    print(f"  Success: {result.success}")
    print(f"  URL: {result.url}")
    print(f"  Post ID: {result.post_id}")

    # --- Schedule a post for Twitter ---
    print("\nScheduling Twitter post...")
    scheduled_time = datetime.utcnow() + timedelta(hours=3)
    sched_result = await twitter.schedule(
        "Don't miss our upcoming announcement! #MediaMaster",
        scheduled_at=scheduled_time,
        networks=["twitter"],
    )
    print(f"  Scheduled: {sched_result.success}")
    print(f"  Schedule ID: {sched_result.schedule_id}")
    print(f"  Time: {sched_result.scheduled_at}")

    # --- Cross-post to all Postiz networks ---
    print("\nCross-posting to all networks...")
    multi_result = await postiz.post(
        "MediaMaster v2 is here! Now supporting 7+ platforms. "
        "Check out the repo: github.com/cyrilolivieri/mediamaster-v2",
        networks=["linkedin", "twitter", "instagram"],
    )
    print(f"  Success: {multi_result.success}")

    # --- Upload a YouTube video ---
    print("\nUploading to YouTube...")
    video_result = await youtube.post(
        "/path/to/your/video.mp4",  # Replace with actual path
        title="MediaMaster v2 Announcement",
        description="Announcing the new multi-platform social media agent.",
        tags=["social media", "automation", "python"],
        privacy_status="public",
    )
    print(f"  Success: {video_result.success}")
    print(f"  URL: {video_result.url}")

    # --- Health checks ---
    print("\nHealth checks...")
    platforms = {"linkedin": linkedin, "twitter": twitter, "youtube": youtube}
    for name, platform in platforms.items():
        healthy = await platform.health_check()
        print(f"  {name}: {'✅' if healthy else '❌'}")

    await postiz.close()


if __name__ == "__main__":
    asyncio.run(main())
