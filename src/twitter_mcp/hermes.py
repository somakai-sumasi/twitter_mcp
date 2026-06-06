import asyncio
import json
import os
from urllib import error, parse, request

HERMES_TWEET_DEFAULT_BASE_URL = "https://api.xquik.com"
HERMES_TWEET_SEARCH_PATH = "/api/v1/x/tweets/search"


def read_backend() -> str:
    return os.getenv("X_READ_BACKEND", "").strip().lower()


def hermes_api_key() -> str | None:
    return os.getenv("HERMES_TWEET_API_KEY") or os.getenv("XQUIK_API_KEY")


def has_hermes_api_key() -> bool:
    return bool(hermes_api_key())


def hermes_base_url() -> str:
    return os.getenv("HERMES_TWEET_BASE_URL", HERMES_TWEET_DEFAULT_BASE_URL).rstrip("/")


def hermes_headers(api_key: str) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "twitter-mcp-hermes-tweet",
    }
    if api_key.startswith("xq_"):
        headers["x-api-key"] = api_key
    else:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _compact_error_body(body: bytes) -> str:
    text = body.decode("utf-8", errors="replace").strip()
    if len(text) > 300:
        return text[:300] + "..."
    return text


def load_json_url(url: str, headers: dict[str, str]) -> object:
    req = request.Request(url, headers=headers)
    try:
        with request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = _compact_error_body(exc.read())
        detail = f": {body}" if body else ""
        raise RuntimeError(f"Hermes Tweet search failed with HTTP {exc.code}{detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Hermes Tweet search request failed: {exc.reason}") from exc


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def extract_hermes_items(payload: object) -> list[object]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []

    for key in ("data", "tweets", "results", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = extract_hermes_items(value)
            if nested:
                return nested
    return []


def _first_value(*values: object) -> object:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _first_int(*values: object) -> int | None:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _normalize_user(item: dict) -> dict | None:
    user = item.get("user") or item.get("author") or {}
    if not isinstance(user, dict):
        user = {}
    screen_name = _first_value(
        user.get("screen_name"),
        user.get("username"),
        user.get("handle"),
        item.get("authorHandle"),
        item.get("author_handle"),
    )
    name = _first_value(user.get("name"), item.get("authorName"), item.get("author_name"))
    user_id = _first_value(user.get("id"), user.get("id_str"), item.get("authorId"), item.get("author_id"))
    if not (screen_name or name or user_id):
        return None
    return {
        "id": str(user_id) if user_id is not None else None,
        "name": name,
        "screen_name": screen_name,
    }


def _normalize_media(value: object) -> list[dict]:
    media = []
    for item in _as_list(value):
        if isinstance(item, str):
            media.append({"url": item})
            continue
        if not isinstance(item, dict):
            continue
        media.append(
            {
                "type": item.get("type"),
                "url": _first_value(item.get("url"), item.get("media_url"), item.get("mediaUrl")),
                "expanded_url": _first_value(item.get("expanded_url"), item.get("expandedUrl")),
            }
        )
    return media


def normalize_hermes_tweet(item: object) -> dict:
    if not isinstance(item, dict):
        return {"id": "", "text": str(item)}

    metrics = item.get("public_metrics") or item.get("metrics") or item.get("engagement") or {}
    if not isinstance(metrics, dict):
        metrics = {}

    normalized = {
        "id": str(_first_value(item.get("id"), item.get("tweet_id"), item.get("tweetId"), item.get("rest_id")) or ""),
        "text": _first_value(item.get("text"), item.get("full_text"), item.get("fullText"), item.get("content")) or "",
        "created_at": _first_value(item.get("created_at"), item.get("createdAt"), item.get("posted_at"), item.get("postedAt")),
        "lang": item.get("lang") or item.get("language"),
        "favorite_count": _first_int(item.get("favorite_count"), item.get("like_count"), metrics.get("like_count"), metrics.get("likes")) or 0,
        "retweet_count": _first_int(item.get("retweet_count"), item.get("repost_count"), metrics.get("retweet_count"), metrics.get("repostCount")) or 0,
        "reply_count": _first_int(item.get("reply_count"), metrics.get("reply_count"), metrics.get("replyCount")) or 0,
        "quote_count": _first_int(item.get("quote_count"), metrics.get("quote_count"), metrics.get("quoteCount")) or 0,
        "bookmark_count": _first_int(item.get("bookmark_count"), metrics.get("bookmark_count"), metrics.get("bookmarkCount")) or 0,
        "view_count": _first_int(item.get("view_count"), item.get("views"), metrics.get("view_count"), metrics.get("impression_count")),
        "hashtags": item.get("hashtags") or [],
        "urls": item.get("urls") or item.get("links") or [],
        "in_reply_to": _first_value(item.get("in_reply_to"), item.get("inReplyToStatusId"), item.get("in_reply_to_status_id")),
        "is_quote_status": bool(item.get("is_quote_status") or item.get("isQuoteStatus")),
        "possibly_sensitive": bool(item.get("possibly_sensitive") or item.get("possiblySensitive")),
    }

    user = _normalize_user(item)
    if user is not None:
        normalized["user"] = user

    media = _normalize_media(item.get("media") or item.get("mediaObjects"))
    if media:
        normalized["media"] = media

    quote = item.get("quote") or item.get("quotedTweet") or item.get("quoted_tweet")
    if quote:
        normalized["quote"] = normalize_hermes_tweet(quote)

    return normalized


async def search_hermes_tweets(query: str, product: str, count: int) -> list[dict]:
    api_key = hermes_api_key()
    if not api_key:
        raise RuntimeError("Set HERMES_TWEET_API_KEY or XQUIK_API_KEY to use the Hermes Tweet backend.")

    params = parse.urlencode({"q": query, "queryType": product, "limit": str(count)})
    url = f"{hermes_base_url()}{HERMES_TWEET_SEARCH_PATH}?{params}"
    payload = await asyncio.to_thread(load_json_url, url, hermes_headers(api_key))
    return [normalize_hermes_tweet(item) for item in extract_hermes_items(payload)]
