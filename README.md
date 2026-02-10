# Twitter MCP Server

[日本語版はこちら](docs/README_ja.md)

A read-only Twitter MCP Server using twikit. Retrieve Twitter data from Claude Code or Claude Desktop.

## Setup

```bash
cd <project-root>
uv sync
python scripts/patch_twikit.py
```

> **Note:** The patch script fixes a known twikit bug ([d60/twikit#375](https://github.com/d60/twikit/issues/375)) where `get_tweet_by_id()` fails with `KeyError: 'itemContent'` due to a Twitter/X API response change. Run it again after upgrading twikit until the issue is resolved upstream.

## Authentication (cookies.json)

The twikit login API is blocked by Cloudflare, so browser cookies are used instead.

Log in to x.com in your browser, export cookies as JSON, and save as `cookies.json` in the project root. Both browser export format (array) and twikit format (dict) are supported.

## Register with Claude Code

```bash
claude mcp add twitter-mcp -- uv run --directory <project-root> python -m twitter_mcp.server
```

## Register with Claude Desktop

Add to `mcpServers` in `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "twitter-mcp": {
    "command": "uv",
    "args": ["run", "--directory", "<project-root>", "python", "-m", "twitter_mcp.server"]
  }
}
```

Restart Claude Desktop to apply.

## Available Tools

| Tool                  | Description                | Parameters                                                   |
| --------------------- | -------------------------- | ------------------------------------------------------------ |
| `search_tweets`       | Search tweets by keyword   | `query`, `product`(Top/Latest/Media), `count`                |
| `get_user_info`       | Get user profile           | `screen_name`                                                |
| `get_user_tweets`     | Get user's tweets          | `user_id`, `tweet_type`(Tweets/Replies/Media/Likes), `count` |
| `get_tweet`           | Get a single tweet         | `tweet_id`                                                   |
| `get_tweet_replies`   | Get replies to a tweet     | `tweet_id`, `count`                                          |
| `get_timeline`        | Get home timeline          | `count`                                                      |
| `get_latest_timeline` | Get latest timeline        | `count`                                                      |
| `get_trends`          | Get trends                 | `category`(trending/for-you/news/sports/entertainment)       |

## Test

```bash
uv run python test_login.py
```
