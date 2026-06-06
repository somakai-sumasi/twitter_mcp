# Twitter MCP Server

[日本語版はこちら](docs/README_ja.md)

A read-only Twitter MCP Server using twikit. Retrieve Twitter data from Claude Code or Claude Desktop.

## Setup

```bash
cd <project-root>
uv sync
python scripts/patch_twikit.py
```

> **Note:** PyPI's twikit has been unreleased since 2025-02 while X kept changing its responses. The patch script applies the upstream fixes (still unmerged on `d60/twikit`) needed to keep this MCP working: `itemContent` defensive access ([#375](https://github.com/d60/twikit/issues/375)), the new `ondemand.s` webpack format for `X-Client-Transaction-Id` ([#408](https://github.com/d60/twikit/issues/408)/[#409](https://github.com/d60/twikit/issues/409)), `User` `legacy.*` field guards, and switching `SearchTimeline` from GET to POST ([#412](https://github.com/d60/twikit/pull/412)/[#419](https://github.com/d60/twikit/pull/419)). Re-run after each `uv sync` until upstream releases a fix.

## Authentication (cookies.json)

The twikit login API is blocked by Cloudflare, so browser cookies are used instead.

Log in to x.com in your browser, export cookies as JSON, and save as `cookies.json` in the project root. Both browser export format (array) and twikit format (dict) are supported.

## Optional Hermes Tweet search backend

`search_tweets` can use Hermes Tweet / Xquik as a read-only search backend when
you do not want to maintain browser cookies for search-only MCP usage. Other
tools still use the authenticated twikit session.

```bash
export X_READ_BACKEND=hermes
export HERMES_TWEET_API_KEY=...
# or
export XQUIK_API_KEY=...
```

With `X_READ_BACKEND=hermes`, `search_tweets` calls
`/api/v1/x/tweets/search` and returns the same JSON array shape as the twikit
path. If no `cookies.json` or Twitter login credentials are available, the MCP
server can still start for read-only Hermes Tweet search when one of these API
keys is configured.

Optional override:

```bash
export HERMES_TWEET_BASE_URL=https://api.xquik.com
```

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
