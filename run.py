import argparse
import asyncio
import json
from pathlib import Path

from twitter_login import Client, UserAgent
from twitter_login.enums import SearchTimelineProduct

UA = UserAgent(
    ch_ua='"Chromium";v="146", "Google Chrome";v="146", "Not-A.Brand";v="24"',
    ch_ua_mobile="?0",
    ch_ua_platform='"Linux"',
    user_agent=(
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    ),
)

COOKIES_PATH = Path(__file__).parent / "cookies.json"
OUTPUT_DIR = Path(__file__).parent / "scraped"

SEARCHES = {
    "account": ("Tweets from a specific account", "from:n_izzah", SearchTimelineProduct.LIVE, 50),
    "hashtag": ("Hashtag", "#PRN", SearchTimelineProduct.TOP, 50),
    "keyword": ("Keyword + filter", "IRAN", SearchTimelineProduct.TOP, 50),
    "date": ("Date range", "IRAN since:2020-01-01 until:2026-06-08", SearchTimelineProduct.LIVE, 50),
}


def tweet_to_dict(tweet) -> dict:
    return {
        "id": tweet.id,
        "text": tweet.full_text,
        "created_at": tweet.created_at,
        "likes": tweet.favorite_count,
        "retweets": tweet.retweet_count,
        "replies": tweet.reply_count,
        "views": tweet.view_count,
        "user_id": tweet.user_id,
        "hashtags": [h.text for h in tweet.full_hashtags],
        "mentions": [m.screen_name for m in tweet.full_mentions],
        "urls": [u.expanded_url for u in tweet.full_urls],
    }


async def scrape_search(client: Client, key: str, pages: int) -> list[dict]:
    label, query, product, count = SEARCHES[key]
    page = await client.search(query, product, count=count)
    rows = []

    for _ in range(pages):
        for tweet in page:
            rows.append(tweet_to_dict(tweet))
        if not page.next_cursor:
            break
        page = await page.next()
        await asyncio.sleep(2)

    print(f"\n{'=' * 60}")
    print(f"{label}: {query}")
    print(f"Scraped {len(rows)} tweets")
    print('=' * 60)
    for row in rows[:5]:
        print(row["id"], (row["text"] or "")[:80])
    if len(rows) > 5:
        print(f"... and {len(rows) - 5} more")

    return rows


def save_scrape(key: str, rows: list[dict], query: str) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    out = OUTPUT_DIR / f"{key}.json"
    payload = {
        "search_key": key,
        "query": query,
        "count": len(rows),
        "tweets": rows,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved → {out}")
    return out


async def main(keys: list[str], pages: int) -> None:
    client = Client(UA)
    await client.load_cookies(str(COOKIES_PATH))

    for key in keys:
        query = SEARCHES[key][1]
        rows = await scrape_search(client, key, pages)
        save_scrape(key, rows, query)
        if len(keys) > 1:
            await asyncio.sleep(2)

    client.save_cookies(str(COOKIES_PATH))
    await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape X searches separately to JSON files.")
    parser.add_argument(
        "search",
        nargs="?",
        choices=[*SEARCHES.keys(), "all"],
        default="all",
        help="which search to scrape (default: all)",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=1,
        help="number of result pages per search (default: 1)",
    )
    args = parser.parse_args()
    keys = list(SEARCHES.keys()) if args.search == "all" else [args.search]
    asyncio.run(main(keys, args.pages))
