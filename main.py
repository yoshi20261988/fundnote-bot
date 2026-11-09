import os
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

TARGETS = [
    {"short_name": "かいほう", "keyword": "Kaihou"},
    {"short_name": "あけぼの", "keyword": "akebono"},
]


def main():
    url = "https://www.fundnote.co.jp/base-price-history/"
    res = requests.get(url, headers=HEADERS, timeout=15)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")
    clean_text = " ".join(soup.get_text().split())

    # 1. サイト上の「基準日」や「基準価額」の周辺文字を表示
    idx = clean_text.find("基準")
    if idx != -1:
        print("【基準周辺の文字】:", clean_text[idx : idx + 200])
    else:
        print("【基準という文字は見つかりませんでした】")

    # 2. 「Kaihou」の周辺文字を表示
    for t in TARGETS:
        if t["keyword"] in clean_text:
            sub = clean_text.split(t["keyword"])[1][:200]
            print(f"【{t['short_name']}の直後の文字】:", sub)
        else:
            print(f"【{t['short_name']}のキーワードが見つかりません】")


if __name__ == "__main__":
    main()
