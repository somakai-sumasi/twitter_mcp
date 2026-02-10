import asyncio
import json
from twikit import Client

COOKIES_FILE = "cookies.json"


def load_browser_cookies(path: str) -> dict:
    """ブラウザエクスポート形式のcookiesをtwikit形式に変換する"""
    with open(path) as f:
        data = json.load(f)

    if isinstance(data, list):
        # ブラウザ拡張の形式 → x.com のcookieだけ抽出して {name: value} に変換
        return {
            c["name"]: c["value"]
            for c in data
            if ".x.com" in c.get("domain", "") or "x.com" in c.get("domain", "")
        }
    return data


async def main():
    print("cookies.json からログイン試行中...")

    client = Client("ja")
    cookies = load_browser_cookies(COOKIES_FILE)
    client.set_cookies(cookies)
    print(f"x.com のcookie {len(cookies)}件を読み込み")

    # cookie が有効か確認するため自分のタイムラインを取得
    results = await client.get_timeline(5)
    print(f"タイムライン取得成功！ {len(results)}件")
    for t in results:
        name = t.user.screen_name if t.user else "?"
        text = (t.text or "")[:60]
        print(f"  @{name}: {text}")


asyncio.run(main())
