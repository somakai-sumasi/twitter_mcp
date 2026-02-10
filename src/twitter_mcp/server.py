import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from mcp.server.fastmcp import FastMCP, Context
from twikit import Client

from twitter_mcp.config import settings

COOKIES_PATH = str(Path(__file__).resolve().parent.parent.parent / "cookies.json")


def _load_cookies(path: str) -> dict:
    """ブラウザエクスポート形式(list)とtwikit形式(dict)の両方に対応"""
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return {
            c["name"]: c["value"]
            for c in data
            if ".x.com" in c.get("domain", "") or "x.com" in c.get("domain", "")
        }
    return data


def _format_tweet(tweet) -> dict:
    result = {
        "id": tweet.id,
        "text": getattr(tweet, "text", "") or getattr(tweet, "full_text", ""),
        "created_at": getattr(tweet, "created_at", None),
        "lang": getattr(tweet, "lang", None),
        "favorite_count": getattr(tweet, "favorite_count", 0),
        "retweet_count": getattr(tweet, "retweet_count", 0),
        "reply_count": getattr(tweet, "reply_count", 0),
        "quote_count": getattr(tweet, "quote_count", 0),
        "bookmark_count": getattr(tweet, "bookmark_count", 0),
        "view_count": getattr(tweet, "view_count", None),
        "hashtags": getattr(tweet, "hashtags", []),
        "urls": getattr(tweet, "urls", []),
        "in_reply_to": getattr(tweet, "in_reply_to", None),
        "is_quote_status": getattr(tweet, "is_quote_status", False),
        "possibly_sensitive": getattr(tweet, "possibly_sensitive", False),
    }
    if hasattr(tweet, "user") and tweet.user:
        result["user"] = {
            "id": tweet.user.id,
            "name": tweet.user.name,
            "screen_name": tweet.user.screen_name,
        }
    if getattr(tweet, "media", None):
        result["media"] = [
            {
                "type": getattr(m, "type", None),
                "url": getattr(m, "media_url", None),
                "expanded_url": getattr(m, "expanded_url", None),
            }
            for m in tweet.media
        ]
    if getattr(tweet, "quote", None):
        result["quote"] = _format_tweet(tweet.quote)
    if getattr(tweet, "retweeted_tweet", None):
        result["retweeted_tweet"] = _format_tweet(tweet.retweeted_tweet)
    if getattr(tweet, "poll", None):
        result["poll"] = str(tweet.poll)
    if getattr(tweet, "place", None):
        result["place"] = str(tweet.place)
    if getattr(tweet, "community_note", None):
        result["community_note"] = str(tweet.community_note)
    return result


def _format_user(user) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "screen_name": user.screen_name,
        "description": getattr(user, "description", ""),
        "location": getattr(user, "location", ""),
        "followers_count": getattr(user, "followers_count", 0),
        "following_count": getattr(user, "following_count", 0),
        "statuses_count": getattr(user, "statuses_count", 0),
        "favourites_count": getattr(user, "favourites_count", 0),
        "verified": getattr(user, "verified", False),
        "is_blue_verified": getattr(user, "is_blue_verified", False),
        "profile_image_url": getattr(user, "profile_image_url", ""),
        "created_at": getattr(user, "created_at", ""),
    }


@asynccontextmanager
async def lifespan(server):
    client = Client("ja")
    if os.path.exists(COOKIES_PATH):
        client.set_cookies(_load_cookies(COOKIES_PATH))
    else:
        await client.login(
            auth_info_1=settings.TWITTER_USERNAME,
            auth_info_2=settings.TWITTER_EMAIL,
            password=settings.TWITTER_PASSWORD,
        )
        client.save_cookies(COOKIES_PATH)
    yield {"client": client}


mcp = FastMCP(
    "twitter-mcp",
    instructions=(
        "Twitter/X コンテンツ取得の代替手段を提供する MCP サーバー。"
        "AI ツールが Twitter/X の URL を直接 fetch すると認証・スクレイピング対策でブロックされるため、"
        "認証済みセッションを経由してこの制約を回避する。"
        "ツイート URL を渡された場合は ID を抽出し get_tweet で内容を取得できる。"
    ),
    lifespan=lifespan,
)


def _get_client(ctx: Context) -> Client:
    return ctx.request_context.lifespan_context["client"]


@mcp.tool()
async def search_tweets(
    ctx: Context,
    query: str,
    product: str = "Top",
    count: int = 20,
) -> str:
    """キーワードでツイートを検索する。productはTop/Latest/Mediaから選択。"""
    client = _get_client(ctx)
    results = await client.search_tweet(query, product, count=count)
    return json.dumps([_format_tweet(t) for t in results], ensure_ascii=False, indent=2)


@mcp.tool()
async def get_user_info(ctx: Context, screen_name: str) -> str:
    """ユーザー名（@なし）からプロフィール情報を取得する。"""
    client = _get_client(ctx)
    user = await client.get_user_by_screen_name(screen_name)
    return json.dumps(_format_user(user), ensure_ascii=False, indent=2)


@mcp.tool()
async def get_user_tweets(
    ctx: Context,
    user_id: str,
    tweet_type: str = "Tweets",
    count: int = 20,
) -> str:
    """ユーザーIDを指定してツイート一覧を取得する。tweet_typeはTweets/Replies/Media/Likesから選択。"""
    client = _get_client(ctx)
    results = await client.get_user_tweets(user_id, tweet_type, count=count)
    return json.dumps([_format_tweet(t) for t in results], ensure_ascii=False, indent=2)


@mcp.tool()
async def get_tweet(ctx: Context, tweet_id: str) -> str:
    """ツイートIDを指定して1件のツイートを取得する。"""
    client = _get_client(ctx)
    tweet = await client.get_tweet_by_id(tweet_id)
    return json.dumps(_format_tweet(tweet), ensure_ascii=False, indent=2)


@mcp.tool()
async def get_timeline(ctx: Context, count: int = 20) -> str:
    """ホームタイムラインを取得する。"""
    client = _get_client(ctx)
    results = await client.get_timeline(count)
    return json.dumps([_format_tweet(t) for t in results], ensure_ascii=False, indent=2)


@mcp.tool()
async def get_latest_timeline(ctx: Context, count: int = 20) -> str:
    """フォロー中ユーザーの最新タイムラインを時系列順で取得する。"""
    client = _get_client(ctx)
    results = await client.get_latest_timeline(count)
    return json.dumps([_format_tweet(t) for t in results], ensure_ascii=False, indent=2)


@mcp.tool()
async def get_tweet_replies(ctx: Context, tweet_id: str, count: int = 20) -> str:
    """ツイートIDを指定してリプライ一覧を取得する。"""
    client = _get_client(ctx)
    tweet = await client.get_tweet_by_id(tweet_id)
    replies = []
    if hasattr(tweet, "replies") and tweet.replies is not None:
        for i, reply in enumerate(tweet.replies):
            if i >= count:
                break
            replies.append(_format_tweet(reply))
    return json.dumps(
        {"tweet": _format_tweet(tweet), "replies": replies},
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
async def get_trends(ctx: Context, category: str = "trending") -> str:
    """トレンドを取得する。categoryはtrending/for-you/news/sports/entertainmentから選択。"""
    client = _get_client(ctx)
    results = await client.get_trends(category)
    trends = []
    for t in results:
        trends.append({
            "name": getattr(t, "name", ""),
            "tweet_count": getattr(t, "tweet_count", None),
            "domain_context": getattr(t, "domain_context", None),
            "grouped_trends": getattr(t, "grouped_trends", None),
        })
    return json.dumps(trends, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
