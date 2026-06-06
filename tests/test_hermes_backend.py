import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from twitter_mcp import hermes, server


class FakeRequestContext:
    def __init__(self, lifespan_context):
        self.lifespan_context = lifespan_context


class FakeContext:
    def __init__(self, lifespan_context):
        self.request_context = FakeRequestContext(lifespan_context)


class HermesBackendTests(unittest.IsolatedAsyncioTestCase):
    def test_hermes_headers_use_x_api_key_for_xquik_keys(self):
        headers = hermes.hermes_headers("xq_test")

        self.assertEqual(headers["x-api-key"], "xq_test")
        self.assertNotIn("Authorization", headers)

    def test_hermes_headers_use_bearer_for_non_xquik_keys(self):
        headers = hermes.hermes_headers("plain-token")

        self.assertEqual(headers["Authorization"], "Bearer plain-token")
        self.assertNotIn("x-api-key", headers)

    def test_normalize_hermes_tweet_matches_existing_output_shape(self):
        normalized = hermes.normalize_hermes_tweet(
            {
                "tweetId": "123",
                "fullText": "Hello from Hermes Tweet",
                "createdAt": "2026-06-06T00:00:00Z",
                "author": {"id": "42", "username": "alice", "name": "Alice"},
                "likeCount": "7",
                "public_metrics": {
                    "retweetCount": 2,
                    "replyCount": "3",
                    "quoteCount": 4,
                    "bookmarkCount": 5,
                    "impressionCount": "600",
                },
                "mediaObjects": [{"type": "photo", "mediaUrl": "https://example.com/a.jpg"}],
            }
        )

        self.assertEqual(normalized["id"], "123")
        self.assertEqual(normalized["text"], "Hello from Hermes Tweet")
        self.assertEqual(normalized["created_at"], "2026-06-06T00:00:00Z")
        self.assertEqual(normalized["favorite_count"], 7)
        self.assertEqual(normalized["retweet_count"], 2)
        self.assertEqual(normalized["reply_count"], 3)
        self.assertEqual(normalized["quote_count"], 4)
        self.assertEqual(normalized["bookmark_count"], 5)
        self.assertEqual(normalized["view_count"], 600)
        self.assertEqual(normalized["user"]["screen_name"], "alice")
        self.assertEqual(normalized["media"][0]["url"], "https://example.com/a.jpg")

    async def test_search_tweets_uses_hermes_backend_when_forced(self):
        calls = []

        def fake_load_json_url(url, headers):
            calls.append((url, headers))
            return {
                "data": [
                    {
                        "id": "999",
                        "text": "Search result",
                        "user": {"screen_name": "bob"},
                    }
                ]
            }

        with patch.dict(
            os.environ,
            {
                "X_READ_BACKEND": "hermes",
                "HERMES_TWEET_API_KEY": "xq_test",
                "HERMES_TWEET_BASE_URL": "https://api.example.test",
            },
        ), patch("twitter_mcp.hermes.load_json_url", side_effect=fake_load_json_url):
            result = await server.search_tweets(FakeContext({"client": object()}), "ai agents", "Latest", 3)

        payload = json.loads(result)
        self.assertEqual(payload[0]["id"], "999")
        self.assertEqual(payload[0]["user"]["screen_name"], "bob")
        self.assertEqual(calls[0][1]["x-api-key"], "xq_test")
        self.assertIn("https://api.example.test/api/v1/x/tweets/search?", calls[0][0])
        self.assertIn("q=ai+agents", calls[0][0])
        self.assertIn("queryType=Latest", calls[0][0])
        self.assertIn("limit=3", calls[0][0])

    async def test_search_tweets_uses_hermes_backend_without_twikit_client(self):
        def fake_load_json_url(url, headers):
            return {"tweets": [{"tweet_id": "321", "text": "Fallback result"}]}

        with patch.dict(
            os.environ,
            {"HERMES_TWEET_API_KEY": "xq_test"},
        ), patch("twitter_mcp.hermes.load_json_url", side_effect=fake_load_json_url):
            result = await server.search_tweets(FakeContext({"client": None}), "fallback", "Top", 1)

        payload = json.loads(result)
        self.assertEqual(payload[0]["id"], "321")
        self.assertEqual(payload[0]["text"], "Fallback result")


if __name__ == "__main__":
    unittest.main()
