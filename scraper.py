import html as _html
import time
import re
from datetime import datetime
from playwright.async_api  import async_playwright, TimeoutError as PlaywrightTimeout

from repository import TweetModel

class Scraper:
    def __init__(self, 
                 username: str, 
                 scroll_pause: int, 
                 max_scrolls: int, 
                 batch_size: int
    ) -> None:
        self.username = username
        self.profile_url = f"https://x.com/{username}"
        self.scroll_pause = scroll_pause
        self.max_scrolls = max_scrolls
        self.headless = True
        self.batch_size = batch_size

    async def parse_inner_text(self, el):
        content = ""
        content_node = await el.query_selector('div[lang]') or el
        try:
            raw_html = await content_node.inner_html()
            # convert <br> and block-end tags to newlines
            raw_html = re.sub(r'(?i)<br\s*/?>', '\n', raw_html)
            raw_html = re.sub(r'(?i)</(div|p|li)>', '\n', raw_html)
            # remove remaining tags
            text = re.sub(r'<[^>]+>', '', raw_html)
            content = _html.unescape(text).strip()
        except Exception:
            content = await el.inner_text().strip()
        return content

    async def parse_tweet(self, el):
        """Extract tweet info from a tweet <article> element."""
        tweet_id = None
        a = await el.query_selector('a[href*="/status/"]')
        if a:
            href = await a.get_attribute("href")
            if href:
                m = re.search(r"/status/(\d+)", href)
                if m:
                    tweet_id = m.group(1)

        time_el = await el.query_selector("time")
        dt = None
        if time_el:
            dt_attr = await time_el.get_attribute("datetime")
            if dt_attr:
                try:
                    dt = datetime.fromisoformat(dt_attr.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass

        # content = el.inner_text().strip()
        content = await self.parse_inner_text(el)
        # print(content)
        async def get_count(sel):
            node = await el.query_selector(sel)
            if node:
                txt = await node.inner_text().strip().replace(",", "")
                try:
                    if txt.lower().endswith("k"):
                        return int(float(txt[:-1]) * 1000)
                    if txt.lower().endswith("m"):
                        return int(float(txt[:-1]) * 1_000_000)
                    return int(txt)
                except Exception:
                    return None
            return None

        return {
            "id": tweet_id,
            "datetime": dt,
            "content": content,
            "reply_count": await get_count('div[data-testid="reply"]'),
            "retweet_count": await get_count('div[data-testid="retweet"]'),
            "like_count": await get_count('div[data-testid="like"]'),
        }

    async def scroll_tweets(self, page):
        seen = set()
        scroll = 0
        box_height_sum = 0
        box_height_count = 0
        tweets_to_store = []
        while scroll < self.max_scrolls:
            print(f"Scroll: {scroll}")
            # ✅ Wait for tweet containers to appear
            print("Waiting for tweets to load...")
            try:
                await page.wait_for_selector('article, div[data-testid="cellInnerDiv"], a[href*="/status/"]', timeout=20000)
                print("Tweets detected!")
            except PlaywrightTimeout:
                print("Timeout waiting for tweet selectors — page may require login or consent.")
            tweets = await page.query_selector_all('article') or page.query_selector_all('div[data-testid="tweetText"]')
            print(f"Scroll {scroll}: Found {len(tweets)} tweet containers.")
            for t in tweets:
                data = await self.parse_tweet(t)
                if not data["id"] or data["id"] in seen:
                    continue
                seen.add(data["id"])
                print(f"- [{data['id']}] {data['datetime']}: {data['content'][:60]!r}")
                tweets_to_store.append(
                    TweetModel(
                        id=data["id"],
                        username=self.username,
                        tweet=data["content"],
                        tweet_dt=data["datetime"],
                        ingestion_dt=datetime.today().strftime('%Y-%m-%d')
                    )
                )
                if len(tweets_to_store) == self.batch_size:
                    yield tweets_to_store.copy()
                    tweets_to_store.clear()

            box = await t.bounding_box()
            if box:
                height = box["height"]
            else:
                # fallback: run in-page JS (returns a float)
                height = t.evaluate("el => el.getBoundingClientRect().height")
            box_height_sum += height
            box_height_count += 1
            box_height_avg = box_height_sum/box_height_count
            print(f"box height: {height}")
            # Scroll down to load more
            # page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            await page.evaluate(f"window.scrollBy(0, {box_height_avg})")
            time.sleep(self.scroll_pause)
            scroll += 1

        if len(tweets_to_store) > 0:
            yield tweets_to_store
    
    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36")
            )
            page = await context.new_page()

            print(f"Opening profile: {self.profile_url}")
            await page.goto(self.profile_url, wait_until="domcontentloaded", timeout=30000)
            async for tweet_batch in self.scroll_tweets(page):
                yield tweet_batch
            # print(f"✅ Done. Collected {len(tweets)} tweets total.")
            await context.close()
            await browser.close()