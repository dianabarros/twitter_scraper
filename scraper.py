import html as _html
import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from repository import TweetModel

class Scraper:
    def __init__(self, 
                 username: str, 
                 scroll_pause: int, 
                 max_scrolls: int, 
                 headless: bool
    ) -> None:
        self.username = username
        self.profile_url = f"https://x.com/{username}"
        self.scroll_pause = scroll_pause
        self.max_scrolls = max_scrolls
        self.headless = headless

    def parse_inner_text(self, el):
        content = ""
        content_node = el.query_selector('div[lang]') or el
        try:
            raw_html = content_node.inner_html()
            # convert <br> and block-end tags to newlines
            raw_html = re.sub(r'(?i)<br\s*/?>', '\n', raw_html)
            raw_html = re.sub(r'(?i)</(div|p|li)>', '\n', raw_html)
            # remove remaining tags
            text = re.sub(r'<[^>]+>', '', raw_html)
            content = _html.unescape(text).strip()
        except Exception:
            content = el.inner_text().strip()
        return content

    def parse_tweet(self, el):
        """Extract tweet info from a tweet <article> element."""
        tweet_id = None
        a = el.query_selector('a[href*="/status/"]')
        if a:
            href = a.get_attribute("href")
            if href:
                m = re.search(r"/status/(\d+)", href)
                if m:
                    tweet_id = m.group(1)

        time_el = el.query_selector("time")
        dt = None
        if time_el:
            dt_attr = time_el.get_attribute("datetime")
            if dt_attr:
                try:
                    dt = datetime.fromisoformat(dt_attr.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass

        # content = el.inner_text().strip()
        content = self.parse_inner_text(el)
        # print(content)
        def get_count(sel):
            node = el.query_selector(sel)
            if node:
                txt = node.inner_text().strip().replace(",", "")
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
            "reply_count": get_count('div[data-testid="reply"]'),
            "retweet_count": get_count('div[data-testid="retweet"]'),
            "like_count": get_count('div[data-testid="like"]'),
        }

    def scroll_tweets(self, page):
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
                page.wait_for_selector('article, div[data-testid="cellInnerDiv"], a[href*="/status/"]', timeout=20000)
                print("Tweets detected!")
            except PlaywrightTimeout:
                print("Timeout waiting for tweet selectors — page may require login or consent.")
            tweets = page.query_selector_all('article') or page.query_selector_all('div[data-testid="tweetText"]')
            print(f"Scroll {scroll}: Found {len(tweets)} tweet containers.")
            for t in tweets:
                data = self.parse_tweet(t)
                if not data["id"] or data["id"] in seen:
                    continue
                seen.add(data["id"])
                print(f"- [{data['id']}] {data['datetime']}: {data['content'][:60]!r}")
                tweets_to_store.append(
                    TweetModel(
                        id=data["id"],
                        username=self.username,
                        tweet=data["content"]
                        tweet_dt=data["datetime"],
                        ingestion_dt=datetime.today().strftime('%Y-%m-%d')
                    )
                )

            box = t.bounding_box()
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
            page.evaluate(f"window.scrollBy(0, {box_height_avg})")
            time.sleep(self.scroll_pause)
            scroll += 1

        return tweets_to_store
    
    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36")
            )
            page = context.new_page()

            print(f"Opening profile: {self.profile_url}")
            page.goto(self.profile_url, wait_until="domcontentloaded", timeout=30000)
            tweets = self.scroll_tweets(page)
            print(f"✅ Done. Collected {len(tweets)} tweets total.")
            context.close()
            browser.close()
            return tweets