#!/usr/bin/env python3
"""保険ルール関連の新着情報を集める。

sources.json の各サイト（RSS または HTML のお知らせ一覧）を取得し、
前回までに見た記事（seen.json）にない新着だけを出力する。
標準ライブラリのみで動く。

使い方:
  python3 watcher/check_updates.py            # 新着を表示して seen.json を更新
  python3 watcher/check_updates.py --dry-run  # seen.json を更新しない
  python3 watcher/check_updates.py --json     # 結果を JSON で出力（自動化用）
"""
import argparse
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "sources.json"
SEEN = HERE / "seen.json"
UA = "Mozilla/5.0 (insurance-hearing watcher)"
MAX_SEEN_PER_SOURCE = 500


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as res:
        raw = res.read()
        charset = res.headers.get_content_charset()
    for enc in filter(None, [charset, "utf-8", "cp932"]):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def parse_rss(body):
    root = ET.fromstring(body.encode("utf-8"))
    items = []
    # RSS 2.0 (<item>) と RSS 1.0/RDF (名前空間付き <item>) の両方に対応
    for el in root.iter():
        if not el.tag.endswith("item"):
            continue
        fields = {child.tag.split("}")[-1]: (child.text or "") for child in el}
        title = clean(fields.get("title"))
        link = (fields.get("link") or "").strip()
        if title and link:
            items.append({
                "title": title,
                "url": link,
                "date": (fields.get("pubDate") or fields.get("date") or "").strip(),
            })
    return items


def parse_html(body, base_url, pattern):
    items, seen_urls = [], set()
    for m in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', body, re.S | re.I):
        url = urljoin(base_url, html.unescape(m.group(1)))
        title = clean(m.group(2))
        if not re.search(pattern, url) or len(title) < 8 or url in seen_urls:
            continue
        seen_urls.add(url)
        items.append({"title": title, "url": url, "date": ""})
    return items


def matches(item, keywords):
    return any(k in item["title"] for k in keywords)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="seen.json を更新しない")
    ap.add_argument("--json", action="store_true", help="JSON で出力する")
    args = ap.parse_args()

    config = json.loads(SOURCES.read_text(encoding="utf-8"))
    seen = json.loads(SEEN.read_text(encoding="utf-8")) if SEEN.exists() else {}
    first_run = not seen
    result = {"checked_at": datetime.now(timezone.utc).isoformat(), "new": [], "errors": []}

    for src in config["sources"]:
        name = src["name"]
        try:
            body = fetch(src["url"])
            if src["type"] == "rss":
                items = parse_rss(body)
            else:
                items = parse_html(body, src["url"], src["link_pattern"])
        except Exception as e:  # 1サイトの失敗で全体を止めない
            result["errors"].append({"source": name, "error": f"{type(e).__name__}: {e}"})
            continue

        if src.get("filter"):
            items = [i for i in items if matches(i, config["keywords"])]
        known = seen.get(name, [])
        known_set = set(known)
        fresh = [i for i in items if i["url"] not in known_set]
        for i in fresh:
            result["new"].append({"source": name, **i})
        seen[name] = ([i["url"] for i in fresh] + known)[:MAX_SEEN_PER_SOURCE]

    if first_run:
        result["note"] = "初回実行のため、現在掲載中の記事をすべて新着として扱っています。"
    if not args.dry_run:
        SEEN.write_text(json.dumps(seen, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    if args.json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        if result.get("note"):
            print(f"※ {result['note']}\n")
        print(f"新着 {len(result['new'])} 件")
        for i in result["new"]:
            print(f"- [{i['source']}] {i['title']}\n  {i['url']}")
        for e in result["errors"]:
            print(f"! 取得失敗 [{e['source']}] {e['error']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
