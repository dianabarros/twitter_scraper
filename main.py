import asyncio
import os

from scraper import Scraper
from repository import TweetRepository
from database import Database

async def main():
    db_url = os.getenv("DB_URL")
    username = os.getenv("USERNAME")
    scroll_pause = os.getenv("SCROLL_PAUSE")
    max_scrolls = os.getenv("MAX_SCROLLS")
    batch_size = os.geten("BATCH_SIZE", 200)

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
    asyncio.run(main())
