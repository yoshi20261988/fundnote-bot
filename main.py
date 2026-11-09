import os
import requests
import tweepy

API_URL = "https://d31w0dmwtc2au2.cloudfront.net/base-price"
API_KEY = "xW75MMRSbLbUfU5KOru3rlvc8AJFgISc0L"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "x-api-key": API_KEY,
    "Content-Type": "application/json",
}

# 判明した公式コード名、略称、比較基準価格
TARGET_FUNDS = [
    {
        "slug": "kaihou",
        "short_name": "かいほう",
        "base_price": 15392,
        "label": "年末比",
    },
    {
        "slug": "saikou",
        "short_name": "さいこう",
        "base_price": 10214,
        "label": "年末比",
    },
    {
        "slug": "dalton",
        "short_name": "だるとん",
        "base_price": 10000,
        "label": "設定来",
    },
    {
        "slug": "akebono",
        "short_name": "あけぼの",
        "base_price": 9682,
        "label": "年末比",
    },
    {
        "slug": "nipponbare",
        "short_name": "にっぽん",
        "base_price": 10000,
        "label": "設定来",
    },
]


def fetch_fund_data(slug):
    url = f"{API_URL}?fund={slug}"
    res = requests.get(url, headers=HEADERS, timeout=10)
    if res.status_code != 200:
        return None

    data = res.json()
    if not isinstance(data, list):
        return None

    for item in data:
        if item.get("active") is True:
            return item

    valid = [d for d in data if d.get("base_price") is not None]
    if valid:
        return sorted(valid, key=lambda x: str(x.get("date", "")))[-1]

    return None


def main():
    fund_lines = []
    latest_date_str = ""

    print("--- fundnote公式APIより最速取得中 ---")

    for fund in TARGET_FUNDS:
        try:
            item = fetch_fund_data(fund["slug"])
            if not item or item.get("base_price") is None:
                print(f"[{fund['short_name']}] データ未公表または準備中")
                continue

            price_int = int(item["base_price"])

            pc = item.get("price_change") or {}
            pct_val = pc.get("percentage")
            daily_pct = float(pct_val) if pct_val is not None else 0.0

            date_raw = str(item.get("date", ""))
            if date_raw and not latest_date_str:
                parts = date_raw.split("-")
                if len(parts) >= 3:
                    latest_date_str = f"{int(parts[1])}/{int(parts[2])}"

            base_p = fund["base_price"]
            diff_pct = ((price_int - base_p) / base_p) * 100

            daily_sign = "+" if daily_pct > 0 else ""
            diff_sign = "+" if diff_pct > 0 else ""

            short_name = fund["short_name"]
            label = fund["label"]
            line = f"・{short_name} {price_int:,}円 (前日{daily_sign}{daily_pct:.1f}% / {label}{diff_sign}{diff_pct:.1f}%)"
            fund_lines.append(line)
            print(f"[{short_name}] 取得成功: {line}")

        except Exception as e:
            print(f"[{fund['short_name']}] 取得エラー: {e}")

    if not fund_lines:
        print("有効なファンドデータを取得できませんでした。")
        return

    if not latest_date_str:
        latest_date_str = "最新"

    # 重複投稿防止チェック
    last_date = ""
    if os.path.exists("last_date.txt"):
        with open("last_date.txt", "r", encoding="utf-8") as f:
            last_date = f.read().strip()

    if latest_date_str != "最新" and latest_date_str == last_date:
        print(f"基準日 {latest_date_str} はすでにツイート済みです。終了します。")
        return

    # ツイート作成
    tweet_text = f"【fundnote】{latest_date_str}\n" + "\n".join(fund_lines)
    print("--- 投稿内容 ---\n" + tweet_text)

    # Xへ投稿（前後の余計な空白を自動カット）
    x_api_key = os.environ.get("X_API_KEY", "").strip()
    x_api_secret = os.environ.get("X_API_KEY_SECRET", "").strip()
    x_token = os.environ.get("X_ACCESS_TOKEN", "").strip()
    x_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET", "").strip()

    print(
        f"キー文字数確認: APIKey={len(x_api_key)}, Token={len(x_token)}"
    )

    client = tweepy.Client(
        consumer_key=x_api_key,
        consumer_secret=x_api_secret,
        access_token=x_token,
        access_token_secret=x_token_secret,
    )
    client.create_tweet(text=tweet_text)

    # 投稿成功した日付を記録
    if latest_date_str != "最新":
        with open("last_date.txt", "w", encoding="utf-8") as f:
            f.write(latest_date_str)
    print("fundnote公式の最新基準価額でツイート完了しました！")


if __name__ == "__main__":
    main()
