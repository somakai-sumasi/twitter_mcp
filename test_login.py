import asyncio
import json
from twikit import Client

COOKIES_FILE = "cookies.json"


def load_browser_cookies(path: str) -> dict:
    """Convert browser-exported cookies to twikit format"""
    with open(path) as f:
        data = json.load(f)

    if isinstance(data, list):
        return {
            c["name"]: c["value"]
            for c in data
            if ".x.com" in c.get("domain", "") or "x.com" in c.get("domain", "")
        }
    return data


async def main():
    print("Loading cookies.json...")

    client = Client("ja")
    cookies = load_browser_cookies(COOKIES_FILE)
    client.set_cookies(cookies)
    print(f"Loaded {len(cookies)} cookies for x.com")

    results = await client.get_timeline(5)
    print(f"Timeline fetched: {len(results)} tweets")
    for t in results:
        name = t.user.screen_name if t.user else "?"
        text = (t.text or "")[:60]
        print(f"  @{name}: {text}")


asyncio.run(main())
