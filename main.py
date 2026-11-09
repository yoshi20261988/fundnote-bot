import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def main():
    url = "https://www.fundnote.co.jp/base-price-history/"
    res = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(res.text, "html.parser")

    print("--- スクリプトとAPIの調査 ---")
    for s in soup.find_all("script"):
        src = s.get("src", "")
        # fundnoteのテーマやカスタムスクリプトを表示
        if src and (
            "fundnote" in src or "theme" in src or "main" in src or "app" in src
        ):
            print("【外部スクリプト】:", src)

        # インラインスクリプト内のURLやAPI設定を探す
        if s.string and (
            "api" in s.string.lower()
            or "ajax" in s.string.lower()
            or "json" in s.string.lower()
        ):
            print("【埋め込み設定】:", s.string.strip()[:200])


if __name__ == "__main__":
    main()
