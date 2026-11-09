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

# 対象ファンドのリスト（表示順、正式名称、略称、比較基準価格、ラベル）
TARGET_FUNDS = [
    {
        "title": "fundnote日本株Kaihouファンド",
        "short_name": "かいほう",
        "base_price": 15392,
        "label": "年末比",
    },
    {
        "title": "fundnoteTOB企業価値ジャッジファンド",
        "short_name": "さいこう",
        "base_price": 10214,
        "label": "年末比",
    },
    {
        "title": "fundnoteダルトンNAVFセレクトファンド",
        "short_name": "だるとん",
        "base_price": 10000,
        "label": "設定来",
    },
    {
        "title": "fundnoteIPOクロスオーバーファンド",
        "short_name": "あけぼの",
        "base_price": 9682,
        "label": "年末比",
    },
    {
        "title": "fundnoteNVI日本バリューファンド",
        "short_name": "にっぽん",
        "base_price": 10000,
        "label": "設定来",
    },
]


def fetch_latest_fund_item(fund_title):
    """fundnote公式APIから最新の有効データを取得"""
    url = f"{API_URL}?fund={requests.utils.quote(fund_title)}"
    res = requests.get(url, headers=HEADERS, timeout=10)
    if res.status_code != 200:
        return None

    data = res.json()
    if not isinstance(data, list):
        return None

    # base_price に数字が入っている有効なデータのみを抽出
    valid_items = [d for d in data if d.get("base_price") is not None]
    if not valid_items:
        return None

    # 日付順で最も新しいデータを採用
    latest_item = sorted(valid_items, key=lambda x: str(x.get("date", "")))[-1]
    return latest_item


def main():
    fund_lines = []
    latest_date_str = ""

    print("--- fundnote公式APIより最新データを取得中 ---")

    for fund in TARGET_FUNDS:
        try:
            item = fetch_latest_fund_item(fund["title"])
            if not item:
                print(f"[{fund['short_name']}] データ未公表または準備中")
                continue

            price_int = int(item["base_price"])

            # 前日比(%)の取得
            pc = item.get("price_change") or {}
            pct_val = pc.get("percentage")
            daily_pct = float(pct_val) if pct_val is not None else 0.0

            # 基準日の取得（例: 2026-11-08 → 11/8）
            date_raw = str(item.get("date", ""))
            if date_raw and not latest_date_str:
                parts = date_raw.split("-")
                if len(parts) >= 3:
                    latest_date_str = f"{int(parts[1])}/{int(parts[2])}"

            # 昨年末比・設定来の計算
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

    # Xへ投稿
    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_KEY_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    client.create_tweet(text=tweet_text)

    # 投稿完了日付を記録
    if latest_date_str != "最新":
        with open("last_date.txt", "w", encoding="utf-8") as f:
            f.write(latest_date_str)
    print("fundnote公式API直結でツイート完了しました！")


if __name__ == "__main__":
    main()
