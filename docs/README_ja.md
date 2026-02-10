# Twitter MCP Server

twikit を使った読み取り専用の Twitter MCP Server。Claude Code から Twitter の情報を取得できる。

## セットアップ

```bash
cd <project-root>
uv sync
```

## 認証（cookies.json の準備）

twikit のログインAPI は Cloudflare にブロックされるため、ブラウザから取得した cookie を使う。

ブラウザで x.com にログインし、cookie を JSON エクスポートしてプロジェクトルートに `cookies.json` として保存する。ブラウザエクスポート形式（配列）と twikit 形式（辞書）の両方に対応。

## Claude Code への登録

```bash
claude mcp add twitter-mcp -- uv run --directory <project-root> python -m twitter_mcp.server
```

## Claude Desktop への登録

`~/Library/Application Support/Claude/claude_desktop_config.json` の `mcpServers` に追加:

```json
{
  "twitter-mcp": {
    "command": "uv",
    "args": ["run", "--directory", "<project-root>", "python", "-m", "twitter_mcp.server"]
  }
}
```

設定後 Claude Desktop を再起動で反映。

## 利用可能なツール

| ツール名              | 説明                         | 主なパラメータ                                               |
| --------------------- | ---------------------------- | ------------------------------------------------------------ |
| `search_tweets`       | キーワードでツイート検索     | `query`, `product`(Top/Latest/Media), `count`                |
| `get_user_info`       | プロフィール取得             | `screen_name`                                                |
| `get_user_tweets`     | ユーザーのツイート一覧       | `user_id`, `tweet_type`(Tweets/Replies/Media/Likes), `count` |
| `get_tweet`           | ツイート1件取得              | `tweet_id`                                                   |
| `get_tweet_replies`   | ツイートのリプライ一覧取得   | `tweet_id`, `count`                                          |
| `get_timeline`        | ホームタイムライン取得       | `count`                                                      |
| `get_latest_timeline` | 最新タイムライン取得（時系列）| `count`                                                      |
| `get_trends`          | トレンド取得                 | `category`(trending/for-you/news/sports/entertainment)       |

## 動作確認

```bash
uv run python test_login.py
```
