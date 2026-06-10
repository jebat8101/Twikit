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
    "account": ("Tweets from a specific account", "from:n_izzah", SearchTimelineProduct.LIVE, 500),
    "hashtag": ("Hashtag", "#PRN", SearchTimelineProduct.TOP, 500),
    "keyword": ("Keyword + filter", "IRAN", SearchTimelineProduct.TOP, 500),
    "date": ("Date range", "IRAN since:2023-01-01 until:2026-06-08", SearchTimelineProduct.LIVE, 500),
}


def user_to_dict(user) -> dict:
    return {
        "id": user.id,
        "screen_name": user.screen_name,
        "name": user.name,
        "followers_count": user.followers_count,
        "following_count": user.following_count,
        "created_at": user.created_at,
    }


def tweet_to_dict(tweet) -> dict:
    row = {
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
    user = tweet.user
    if user:
        row["screen_name"] = user.screen_name
        row["user_name"] = user.name
        row["followers_count"] = user.followers_count
    return row


def screen_name_from_query(query: str) -> str | None:
    if query.startswith("from:"):
        return query.removeprefix("from:").split()[0]
    return None


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


def save_scrape(key: str, rows: list[dict], query: str, user: dict | None = None) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    out = OUTPUT_DIR / f"{key}.json"
    payload = {
        "search_key": key,
        "query": query,
        "count": len(rows),
        "tweets": rows,
    }
    if user:
        payload["user"] = user
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved → {out}")
    return out


async def lookup_user(client: Client, screen_name: str) -> dict:
    user = await client.get_user_by_screen_name(screen_name)
    info = user_to_dict(user)
    print(f"\n{'=' * 60}")
    print(f"@{info['screen_name']} ({info['name']})")
    print(f"User ID: {info['id']}")
    print(f"Followers: {info['followers_count']:,}")
    print('=' * 60)
    return info


async def main(keys: list[str], pages: int, user_screen_name: str | None = None) -> None:
    client = Client(UA)
    await client.load_cookies(str(COOKIES_PATH))

    if user_screen_name:
        info = await lookup_user(client, user_screen_name)
        OUTPUT_DIR.mkdir(exist_ok=True)
        out = OUTPUT_DIR / f"user_{user_screen_name}.json"
        out.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved → {out}")
        client.save_cookies(str(COOKIES_PATH))
        await client.close()
        return

    for key in keys:
        query = SEARCHES[key][1]
        rows = await scrape_search(client, key, pages)
        user = None
        screen_name = screen_name_from_query(query)
        if screen_name:
            user = await lookup_user(client, screen_name)
        save_scrape(key, rows, query, user=user)
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
    parser.add_argument(
        "--user",
        metavar="SCREEN_NAME",
        help="look up user id and follower count for a screen name",
    )
    args = parser.parse_args()
    keys = list(SEARCHES.keys()) if args.search == "all" else [args.search]
    asyncio.run(main(keys, args.pages, user_screen_name=args.user))
