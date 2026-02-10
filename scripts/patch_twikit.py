"""twikit の既知バグ (d60/twikit#375) を修正するパッチスクリプト。

Twitter/X の API レスポンス構造変更により get_tweet_by_id() が
KeyError: 'itemContent' で失敗する問題を回避する。

Usage:
    python scripts/patch_twikit.py
"""

import importlib.util
from pathlib import Path


def find_twikit_client() -> Path:
    spec = importlib.util.find_spec("twikit.client.client")
    if spec is None or spec.origin is None:
        raise RuntimeError("twikit がインストールされていません")
    return Path(spec.origin)


PATCHES = [
    # 1) _get_more_replies のカーソル取得 (line ~1526)
    {
        "old": "entries[-1]['content']['itemContent']['value']\n            _fetch_next_result = partial(self._get_more_replies, tweet_id, next_cursor)",
        "new": (
            "entries[-1]['content'].get('itemContent', entries[-1]['content']).get('value')\n"
            "            _fetch_next_result = partial(self._get_more_replies, tweet_id, next_cursor)"
        ),
    },
    # 2) _show_more_replies 内のカーソル取得 (line ~1616)
    {
        "old": "sr_cursor = reply['item']['itemContent']['value']",
        "new": "sr_cursor = reply['item'].get('itemContent', reply['item']).get('value')",
    },
    # 3) get_tweet_by_id のリプライカーソル取得 (line ~1635)
    {
        "old": "reply_next_cursor = entries[-1]['content']['itemContent']['value']",
        "new": "reply_next_cursor = entries[-1]['content'].get('itemContent', entries[-1]['content']).get('value')",
    },
]


def apply_patches(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    patched = False

    for i, patch in enumerate(PATCHES, 1):
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
        print(f"\nPatched: {path}")
    else:
        print("\nNo changes needed.")


def main() -> None:
    path = find_twikit_client()
    print(f"twikit client: {path}\n")
    apply_patches(path)


if __name__ == "__main__":
    main()
