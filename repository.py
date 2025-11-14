from datetime import date, datetime
from typing import List

from pydantic import BaseModel

class TweetModel(BaseModel):
    id: int
    username: str
    tweet: str
    tweet_dt: datetime
    ingestion_dt: date

class TweetRepository:
    def __init__(self, db):
        self.db = db

    async def insert_tweet(self, tweet: TweetModel):
        query = """
            INSERT INTO user_tweets (id, username, tweet, tweet_dt, ingestion_dt)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO NOTHING
        """
        try:
            async with self.db.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        query, 
                        tweet.id, 
                        tweet.username, 
                        tweet.tweet, 
                        tweet.tweet_dt, 
                        tweet.ingestion_dt
                    )
        except Exception as e:
            print(f"[ERROR] Failed to insert tweet {tweet.id}: {e}")

    async def batch_insert(self, tweets: List[TweetModel]):
        if not tweets:
            return

        query = """
            INSERT INTO user_tweets (id, username, tweet, tweet_dt, ingestion_dt)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO NOTHING
        """

        values = [
            (t.id, t.username, t.tweet, t.tweet_dt, t.ingestion_dt)
            for t in tweets
        ]

        try:
            async with self.db.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.executemany(query, values)
        except Exception as e:
            print(f"[ERROR] Failed batch insert: {e}")

    async def get_latest_tweet_id(self):
        query = "SELECT id from user_tweets ORDER BY tweet_dt DESC LIMIT 1"
        async with self.db.pool.acquire() as conn:
            return await conn.fetchrow(query)

    async def get_tweet(self, tweet_id: str):
        query = "SELECT * FROM user_tweets WHERE id = $1"
        async with self.db.pool.acquire() as conn:
            return await conn.fetchrow(query, tweet_id)

    async def get_all(self, limit=100):
        query = "SELECT * FROM user_tweets ORDER BY tweet_dt DESC LIMIT $1"
        async with self.db.pool.acquire() as conn:
            return await conn.fetch(query, limit)
