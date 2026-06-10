<img width="679" height="406" alt="Screenshot_202" src="https://github.com/user-attachments/assets/b3fcad31-935a-4c02-abfc-4ba82ffaf1aa" />

# Twikit

Python library and CLI for authenticating with X (Twitter) via cookies and scraping search results to JSON.

Repository: [https://github.com/jebat8101/Twikit](https://github.com/jebat8101/Twikit)

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Python 3.10+** | Tested with Python 3.10–3.13 |
| **Git** | To clone the repository |
| **Build tools** (Linux) | Required for `stpyv8` (V8 JavaScript bindings) |

On Debian/Kali:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip build-essential
```

---

## Step 1 — Clone the repository

```bash
git clone https://github.com/jebat8101/Twikit.git
cd Twikit
```

---

## Step 2 — Create a virtual environment

```bash
python3 -m venv venv && source venv/bin/activate
```

On Windows:

```bash
venv\Scripts\activate
```

---

## Step 3 — Install dependencies

**Option A — pip (recommended)**

```bash
pip install --upgrade pip
pip install -e .
```

**Option B — uv (if installed)**

```bash
uv sync
```

**Optional — media upload extras**

```bash
pip install -e ".[all]"
```

**Optional — dev tools**

```bash
pip install colorlog tqdm
```

---

## Step 4 — Verify installation

```bash
python -c "import twitter_login; import STPyV8; import curl_cffi; print('Install OK')"
```

If `STPyV8` fails to install:

```bash
sudo apt install -y build-essential
pip install --force-reinstall stpyv8
```

---

## Step 5 — Export X/Twitter cookies

The scraper requires a `cookies.json` file in the project root. It must be a **JSON object** mapping cookie names to values:

```json
{
  "auth_token": "your_auth_token",
  "ct0": "your_ct0_token"
}
```

### Method A — Browser extension (included)

1. Open Chrome or Chromium and go to `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked**
4. Select the `export_cookies/` folder from this repository
5. Log in to [https://x.com](https://x.com) in the same browser
6. Click the extension icon and copy the JSON from the popup
7. Save it as `cookies.json` in the project root:

```bash
nano cookies.json
```

### Method B — Manual export

From browser DevTools → **Application** → **Cookies** → `x.com`, copy at least:

- `auth_token`
- `ct0`

Save them as `cookies.json` in the project root (same folder as `run.py`).

> **Security:** `cookies.json` is listed in `.gitignore`. Never commit or push cookie files.

---

## Step 6 — Run the scraper

Run all four built-in searches (output saved under `scraped/`):

```bash
python3 run.py
```

Run a single search:

```bash
python3 run.py account
python3 run.py hashtag
python3 run.py keyword
python3 run.py date
```


Scrape more result pages per search:

```bash
python3 run.py all --pages 3
python3 run.py keyword --pages 2
```

Output files:

- `scraped/account.json`
- `scraped/hashtag.json`
- `scraped/keyword.json`
- `scraped/date.json`

---

## Step 7 — Customize searches (optional)

Edit the `SEARCHES` dictionary in `run.py`:

```python
SEARCHES = {
    "account": ("Tweets from a specific account", "from:username", SearchTimelineProduct.LIVE, 50),
    "hashtag": ("Hashtag", "#YourTag", SearchTimelineProduct.TOP, 50),
    "keyword": ("Keyword + filter", "your keyword", SearchTimelineProduct.TOP, 50),
    "date": ("Date range", "keyword since:2020-01-01 until:2026-06-08", SearchTimelineProduct.LIVE, 50),
}
```

---

## Use as a Python library

```python
import asyncio
from twitter_login import Client, UserAgent

UA = UserAgent(
    ch_ua='"Chromium";v="146", "Google Chrome";v="146", "Not-A.Brand";v="24"',
    ch_ua_mobile="?0",
    ch_ua_platform='"Linux"',
    user_agent=(
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    ),
)

async def main():
    client = Client(UA)
    await client.load_cookies("cookies.json")
    tweets = await client.search("python", count=20)
    for tweet in tweets:
        print(tweet.full_text)
    await client.close()

asyncio.run(main())
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `"auth_token" not found in cookies` | Re-export cookies while logged in to X |
| `Failed to get ct0 cookie` | `auth_token` is expired — log in again and re-export |
| `STPyV8` install fails | Install `build-essential`, then `pip install --force-reinstall stpyv8` |
| Rate limits or empty results | Lower `--pages`, add delays between runs, or refresh cookies |
| `cookies.json` not found | Create the file in the project root next to `run.py` |

---

## Quick start (full flow)

```bash
git clone https://github.com/jebat8101/Twikit.git
cd Twikit
python3 -m venv venv && source venv/bin/activate
pip install -e .
# export cookies and save as cookies.json
python3 run.py
```

---

## Project structure

```
Twikit/
├── export_cookies/     # Chrome extension to export X cookies
├── twitter_login/      # Core Python package
├── run.py              # CLI scraper entry point
├── pyproject.toml      # Package metadata and dependencies
├── uv.lock             # Locked dependencies (for uv)
└── cookies.json        # Your session cookies (not in git)
```
