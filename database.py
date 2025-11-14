import asyncpg

class Database:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool = None

    async def connect(self):
        # Create a connection pool (recommended for Neon)
        self.pool = await asyncpg.create_pool(self.db_url, min_size=1, max_size=5)

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def get_conn(self):
        if not self.pool:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.pool.acquire()
