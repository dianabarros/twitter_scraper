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
    headless = os.getenv("HEADLESS", False)

    db = Database(db_url)
    db.connect()
    repo = TweetRepository(db)
    
    scraper = Scraper(
        username=username,
        scroll_pause=scroll_pause,
        max_scrolls=max_scrolls,
        headless=headless
    )

    tweets = scraper.run()
    await repo.batch_insert(tweets)

    db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
