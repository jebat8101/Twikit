import argparse
import asyncio
import json
import re
from collections import Counter
from datetime import datetime, timedelta
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
    "date": ("Date range", "IRAN since:2023-01-01 until:2023-06-30", SearchTimelineProduct.LIVE, 500),
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


def parse_date_range(query: str) -> tuple[datetime, datetime] | None:
    since_match = re.search(r"since:(\d{4}-\d{2}-\d{2})", query)
    until_match = re.search(r"until:(\d{4}-\d{2}-\d{2})", query)
    if not (since_match and until_match):
        return None
    since = datetime.strptime(since_match.group(1), "%Y-%m-%d")
    until = datetime.strptime(until_match.group(1), "%Y-%m-%d")
    if since >= until:
        raise ValueError(f"Invalid date range in query: since must be before until ({query})")
    return since, until


def date_range_labels(query: str) -> tuple[str, str] | None:
    parsed = parse_date_range(query)
    if not parsed:
        return None
    since, until = parsed
    return since.strftime("%Y-%m-%d"), until.strftime("%Y-%m-%d")


def slugify_filename_part(text: str) -> str:
    slug = re.sub(r"[^\w#@.-]+", "_", text.strip(), flags=re.UNICODE)
    return slug.strip("_") or "search"


def output_filename(key: str, query: str) -> str:
    labels = date_range_labels(query)
    if labels:
        since, until = labels
        keyword = slugify_filename_part(strip_date_operators(query))
        return f"{keyword}_since_{since}_until_{until}.json"
    return f"{key}.json"


def strip_date_operators(query: str) -> str:
    base = re.sub(r"\s*since:\d{4}-\d{2}-\d{2}", "", query)
    return re.sub(r"\s*until:\d{4}-\d{2}-\d{2}", "", base).strip()


def apply_date_range(query: str, since: str | None, until: str | None) -> str:
    base = strip_date_operators(query)
    if since:
        base = f"{base} since:{since}"
    if until:
        base = f"{base} until:{until}"
    return base.strip()


def resolve_query(key: str, query_override: str | None, since: str | None, until: str | None) -> str:
    query = query_override if query_override is not None else SEARCHES[key][1]
    if since or until:
        existing = parse_date_range(query)
        use_since = since or (existing[0].strftime("%Y-%m-%d") if existing else None)
        use_until = until or (existing[1].strftime("%Y-%m-%d") if existing else None)
        if not (use_since and use_until):
            raise ValueError("Date range requires both --since and --until (or a query with since:/until:)")
        query = apply_date_range(query, use_since, use_until)
    return query


def chunk_date_query(query: str, chunk_days: int) -> list[str]:
    date_range = parse_date_range(query)
    if not date_range:
        return [query]

    since, until = date_range
    base = strip_date_operators(query)
    chunks: list[str] = []
    start = since
    while start < until:
        end = min(start + timedelta(days=chunk_days), until)
        chunks.append(f"{base} since:{start:%Y-%m-%d} until:{end:%Y-%m-%d}")
        start = end
    return chunks


def tweet_year_distribution(rows: list[dict]) -> dict[str, int]:
    years: Counter[str] = Counter()
    for row in rows:
        created_at = row.get("created_at") or ""
        parts = created_at.split()
        if parts:
            years[parts[-1]] += 1
    return dict(sorted(years.items()))


async def scrape_query_pages(
    client: Client,
    query: str,
    product: SearchTimelineProduct,
    count: int,
    pages: int,
) -> list[dict]:
    page = await client.search(query, product, count=count)
    rows: list[dict] = []

    for _ in range(pages):
        for tweet in page:
            rows.append(tweet_to_dict(tweet))
        if not page.next_cursor:
            break
        page = await page.next()
        await asyncio.sleep(2)

    return rows


async def scrape_search(
    client: Client,
    key: str,
    pages: int,
    query: str,
    chunk_days: int | None = None,
) -> tuple[list[dict], list[str]]:
    label, _, product, count = SEARCHES[key]
    queries = chunk_date_query(query, chunk_days) if chunk_days else [query]
    seen_ids: set[str] = set()
    rows: list[dict] = []

    for index, chunk_query in enumerate(queries, start=1):
        if len(queries) > 1:
            print(f"\n--- chunk {index}/{len(queries)}: {chunk_query} ---")
        chunk_rows = await scrape_query_pages(client, chunk_query, product, count, pages)
        for row in chunk_rows:
            tweet_id = str(row["id"])
            if tweet_id in seen_ids:
                continue
            seen_ids.add(tweet_id)
            rows.append(row)
        if len(queries) > 1 and index < len(queries):
            await asyncio.sleep(2)

    print(f"\n{'=' * 60}")
    print(f"{label}: {query}")
    if len(queries) > 1:
        print(f"Chunks: {len(queries)} x {pages} page(s) each")
    print(f"Scraped {len(rows)} unique tweets")
    year_dist = tweet_year_distribution(rows)
    if year_dist:
        print(f"Years: {year_dist}")
    print('=' * 60)
    for row in rows[:5]:
        print(row["id"], row.get("created_at", ""), (row["text"] or "")[:60])
    if len(rows) > 5:
        print(f"... and {len(rows) - 5} more")

    return rows, queries


def save_scrape(
    key: str,
    rows: list[dict],
    query: str,
    queries: list[str] | None = None,
    user: dict | None = None,
) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    out = OUTPUT_DIR / output_filename(key, query)
    payload = {
        "search_key": key,
        "title": query,
        "query": query,
        "count": len(rows),
        "year_distribution": tweet_year_distribution(rows),
        "tweets": rows,
    }
    labels = date_range_labels(query)
    if labels:
        payload["since"], payload["until"] = labels
    if queries and len(queries) > 1:
        payload["chunks"] = queries
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


async def main(
    keys: list[str],
    pages: int,
    user_screen_name: str | None = None,
    chunk_days: int | None = None,
    query_override: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> None:
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
        query = resolve_query(key, query_override, since, until)
        use_chunk_days = chunk_days
        if use_chunk_days is None and key == "date" and parse_date_range(query):
            use_chunk_days = 30
        rows, queries = await scrape_search(client, key, pages, query, chunk_days=use_chunk_days)
        user = None
        screen_name = screen_name_from_query(query)
        if screen_name:
            user = await lookup_user(client, screen_name)
        save_scrape(key, rows, query, queries=queries, user=user)
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
        help="number of result pages per search or per date chunk (default: 1)",
    )
    parser.add_argument(
        "--chunk-days",
        type=int,
        default=None,
        metavar="N",
        help=(
            "split since/until queries into N-day windows (default: 30 for date search). "
            "Use 0 to disable chunking."
        ),
    )
    parser.add_argument(
        "-q",
        "--query",
        metavar="TEXT",
        help='search text, e.g. "IRAN" or full "IRAN since:2023-01-01 until:2023-06-30"',
    )
    parser.add_argument(
        "--since",
        metavar="YYYY-MM-DD",
        help="start date for date-range scrape (use with --until)",
    )
    parser.add_argument(
        "--until",
        metavar="YYYY-MM-DD",
        help="end date for date-range scrape, exclusive (use with --since)",
    )
    parser.add_argument(
        "--user",
        metavar="SCREEN_NAME",
        help="look up user id and follower count for a screen name",
    )
    args = parser.parse_args()
    keys = list(SEARCHES.keys()) if args.search == "all" else [args.search]
    chunk_days = None if args.chunk_days == 0 else args.chunk_days
    asyncio.run(
        main(
            keys,
            args.pages,
            user_screen_name=args.user,
            chunk_days=chunk_days,
            query_override=args.query,
            since=args.since,
            until=args.until,
        )
    )
