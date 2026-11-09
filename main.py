import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def main():
    # 1. あけぼのの個別ページでどんな引数を渡しているか確認
    url = "https://www.fundnote.co.jp/fund/akebono/"
    res = requests.get(url, headers=HEADERS, timeout=15)
    print("--- あけぼのページ内の呼び出しスクリプト ---")
    for line in res.text.split("\n"):
        if any(
            k in line
            for k in [
                "fetchSummary",
                "fundTitle",
                "base-price",
                "fundnoteBasePrice",
            ]
        ):
            print("【呼び出し】:", line.strip()[:200])

    # 2. JSの中身の後半（呼び出し部分）を確認
    js_url = "https://www.fundnote.co.jp/wp-content/themes/fundnote/js/base-price-summary.js"
    res_js = requests.get(js_url, headers=HEADERS, timeout=15)
    print("--- base-price-summary.js の後半 ---")
    print(res_js.text[600:1800])


if __name__ == "__main__":
    main()
