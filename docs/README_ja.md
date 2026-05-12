# Twitter MCP Server

twikit を使った読み取り専用の Twitter MCP Server。Claude Code から Twitter の情報を取得できる。

## セットアップ

```bash
cd <project-root>
uv sync
python scripts/patch_twikit.py
```

> **注意:** PyPI の twikit は 2025-02 以降リリースが止まっており、その間に X 側の仕様変更で複数のバグが発生したまま残っています。パッチスクリプトは、upstream に PR は出ているがまだマージされていない以下の修正をローカル適用します: `itemContent` の防御的アクセス ([#375](https://github.com/d60/twikit/issues/375))、`ondemand.s` の新 webpack 形式対応で `X-Client-Transaction-Id` を復活 ([#408](https://github.com/d60/twikit/issues/408)/[#409](https://github.com/d60/twikit/issues/409))、`User` 初期化時の `legacy.*` キー欠落対策、`SearchTimeline` を GET から POST に変更 ([#412](https://github.com/d60/twikit/pull/412)/[#419](https://github.com/d60/twikit/pull/419))。`uv sync` のたびに再実行してください。

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
