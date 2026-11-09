import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def main():
    url = "https://www.fundnote.co.jp/wp-content/themes/fundnote/js/base-price-summary.js"
    res = requests.get(url, headers=HEADERS, timeout=15)
    print("=== JSの中身 ===")
    print(res.text[:1500])


if __name__ == "__main__":
    main()
