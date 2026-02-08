import asyncio
import os
from dotenv import load_dotenv

from scraper import Scraper
from repository import TweetRepository
from database import Database

async def main():
    db_url = os.getenv("DB_URL")
    username = os.getenv("USERNAME")
    if not username or not db_url:
        print("username and db_url are required")
        exit(1)

    scroll_pause = os.getenv("SCROLL_PAUSE", 1)
    max_scrolls = os.getenv("MAX_SCROLLS", 200)
    batch_size = os.getenv("BATCH_SIZE", 200)

    db = Database(db_url)
    await db.connect()
    repo = TweetRepository(db)
    
    scraper = Scraper(
        username=username,
        scroll_pause=scroll_pause,
        max_scrolls=max_scrolls,
        batch_size=batch_size
    )

    async for tweet_batch in scraper.run():
        await repo.batch_insert(tweet_batch)

    await db.disconnect()


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
