"""twikit (PyPI 2.3.3) に未取り込みの修正を適用するパッチスクリプト。

PyPI 版 twikit は 2025-02 から更新が止まっており、その後の X 側仕様変更で
以下のバグが残っている。いずれも upstream PR は存在するが未マージのため、
本リポジトリではインストール直後にローカルパッチを当てることで対応する。

  1. d60/twikit#375  : get_tweet_by_id() が KeyError: 'itemContent' で失敗
  2. d60/twikit#408/#409 : X-Client-Transaction-Id 生成で
       "Couldn't get KEY_BYTE indices" / "ClientTransaction has no attribute 'key'"
       (X が ondemand.s 参照を新しい webpack チャンク形式に変更)
  3. User 初期化時の KeyError: 'pinned_tweet_ids_str' / 'urls'
       (X のレスポンスで legacy.entities.description.urls 等が省略される)
  4. d60/twikit#412/#419 : SearchTimeline が HTTP 404
       (X が GET を廃止して POST のみ受け付けるよう変更)

Usage:
    python scripts/patch_twikit.py
"""

import importlib.util
from pathlib import Path


def find_module_path(module_name: str) -> Path:
    spec = importlib.util.find_spec(module_name)
    if spec is None or spec.origin is None:
        raise RuntimeError(f"{module_name} が見つかりません (twikit 未インストール?)")
    return Path(spec.origin)


# --- twikit/client/client.py: get_tweet_by_id 周辺の itemContent 直接アクセス ---
CLIENT_PATCHES = [
    {
        "old": "entries[-1]['content']['itemContent']['value']\n            _fetch_next_result = partial(self._get_more_replies, tweet_id, next_cursor)",
        "new": (
            "entries[-1]['content'].get('itemContent', entries[-1]['content']).get('value')\n"
            "            _fetch_next_result = partial(self._get_more_replies, tweet_id, next_cursor)"
        ),
    },
    {
        "old": "sr_cursor = reply['item']['itemContent']['value']",
        "new": "sr_cursor = reply['item'].get('itemContent', reply['item']).get('value')",
    },
    {
        "old": "reply_next_cursor = entries[-1]['content']['itemContent']['value']",
        "new": "reply_next_cursor = entries[-1]['content'].get('itemContent', entries[-1]['content']).get('value')",
    },
]


# --- twikit/x_client_transaction/transaction.py: ondemand.s を新形式で参照 ---
# 参考: d60/twikit PR #416
TRANSACTION_PATCHES = [
    {
        "old": (
            'ON_DEMAND_FILE_REGEX = re.compile(\n'
            '    r"""[\'|\\"]{1}ondemand\\.s[\'|\\"]{1}:\\s*[\'|\\"]{1}([\\w]*)[\'|\\"]{1}""", flags=(re.VERBOSE | re.MULTILINE))\n'
            'INDICES_REGEX = re.compile(\n'
            '    r"""(\\(\\w{1}\\[(\\d{1,2})\\],\\s*16\\))+""", flags=(re.VERBOSE | re.MULTILINE))'
        ),
        "new": (
            'ON_DEMAND_FILE_REGEX = re.compile(\n'
            '    r\',(\\d+):["\\\']ondemand\\.s["\\\']\', flags=(re.VERBOSE | re.MULTILINE))\n'
            'ON_DEMAND_HASH_PATTERN = r\',{}:"([0-9a-f]+)"\'\n'
            'INDICES_REGEX = re.compile(r\'\\[(\\d+)\\],\\s*16\')'
        ),
    },
    {
        "old": (
            "        on_demand_file = ON_DEMAND_FILE_REGEX.search(str(response))\n"
            "        if on_demand_file:\n"
            "            on_demand_file_url = f\"https://abs.twimg.com/responsive-web/client-web/ondemand.s.{on_demand_file.group(1)}a.js\"\n"
            "            on_demand_file_response = await session.request(method=\"GET\", url=on_demand_file_url, headers=headers)\n"
            "            key_byte_indices_match = INDICES_REGEX.finditer(\n"
            "                str(on_demand_file_response.text))\n"
            "            for item in key_byte_indices_match:\n"
            "                key_byte_indices.append(item.group(2))"
        ),
        "new": (
            "        on_demand_match = ON_DEMAND_FILE_REGEX.search(str(response))\n"
            "        if on_demand_match:\n"
            "            chunk_index = on_demand_match.group(1)\n"
            "            hash_match = re.search(\n"
            "                ON_DEMAND_HASH_PATTERN.format(chunk_index), str(response))\n"
            "            if hash_match:\n"
            "                file_hash = hash_match.group(1)\n"
            "                on_demand_file_url = f\"https://abs.twimg.com/responsive-web/client-web/ondemand.s.{file_hash}a.js\"\n"
            "                on_demand_file_response = await session.request(method=\"GET\", url=on_demand_file_url, headers=headers)\n"
            "                for item in INDICES_REGEX.finditer(on_demand_file_response.text):\n"
            "                    key_byte_indices.append(item.group(1))"
        ),
    },
]


# --- twikit/user.py: legacy フィールドが省略されたケースの KeyError 対策 ---
# X のレスポンスは legacy フィールドの一部 (pinned_tweet_ids_str / withheld_in_countries /
# entities.description.urls など) を予告なく省くことがあるため、legacy 辞書全体を
# defaultdict にラップして欠落キーで KeyError を出さないようにする。
# 入れ子の entities.description.urls / entities.url.urls だけは defaultdict では
# カバーできないので個別に防御する。
USER_PATCHES = [
    {
        "old": "from .utils import timestamp_to_datetime",
        "new": "from collections import defaultdict\n\nfrom .utils import timestamp_to_datetime",
    },
    {
        "old": "        legacy = data['legacy']",
        "new": "        legacy = defaultdict(lambda: None, data['legacy'])",
    },
    {
        "old": "        self.description_urls: list = legacy['entities']['description']['urls']",
        "new": "        self.description_urls: list = (legacy['entities'] or {}).get('description', {}).get('urls', [])",
    },
    {
        "old": "        self.urls: list = legacy['entities'].get('url', {}).get('urls')",
        "new": "        self.urls: list = (legacy['entities'] or {}).get('url', {}).get('urls')",
    },
]


# --- twikit/client/gql.py: SearchTimeline の GET が 404 になるため POST 化 ---
# 参考: d60/twikit PR #412
GQL_PATCHES = [
    {
        "old": "        return await self.gql_get(Endpoint.SEARCH_TIMELINE, variables, FEATURES)",
        "new": "        return await self.gql_post(Endpoint.SEARCH_TIMELINE, variables, FEATURES)",
    },
]


TARGETS = [
    ("twikit.client.client", CLIENT_PATCHES),
    ("twikit.x_client_transaction.transaction", TRANSACTION_PATCHES),
    ("twikit.user", USER_PATCHES),
    ("twikit.client.gql", GQL_PATCHES),
]


def apply_patches(path: Path, patches: list[dict]) -> None:
    source = path.read_text(encoding="utf-8")
    patched = False

    for i, patch in enumerate(patches, 1):
        if patch["old"] in source:
            source = source.replace(patch["old"], patch["new"])
            print(f"  patch {i}: applied")
            patched = True
        elif patch["new"] in source:
            print(f"  patch {i}: already applied (skip)")
        else:
            print(f"  patch {i}: target not found (skip)")

    if patched:
        path.write_text(source, encoding="utf-8")
        print(f"  -> wrote {path}")
    else:
        print("  -> no changes needed")


def main() -> None:
    for module_name, patches in TARGETS:
        path = find_module_path(module_name)
        print(f"[{module_name}] {path}")
        apply_patches(path, patches)
        print()


if __name__ == "__main__":
    main()
