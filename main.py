import os
import re
import requests
from bs4 import BeautifulSoup
import tweepy

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

# fundnote公式サイトの個別ページと設定値
TARGET_FUNDS = [
    {
        "short_name": "かいほう",
        "url": "https://www.fundnote.co.jp/fund/kaihou/",
        "base_price": 15392,
        "label": "年末比",
    },
    {
        "short_name": "さいこう",
        "url": "https://www.fundnote.co.jp/fund/saikou/",
        "base_price": 10214,
        "label": "年末比",
    },
    {
        "short_name": "だるとん",
        "url": "https://www.fundnote.co.jp/fund/dalton/",
        "base_price": 10000,
        "label": "設定来",
    },
    {
        "short_name": "あけぼの",
        "url": "https://www.fundnote.co.jp/fund/akebono/",
        "base_price": 9682,
        "label": "年末比",
    },
    {
        "short_name": "にっぽん",
        "url": "https://www.fundnote.co.jp/fund/nipponbare/",
        "base_price": 10000,
        "label": "設定来",
    },
]


def fetch_from_official_fundnote(fund):
    """fundnote公式サイトの個別ページから最速で直接取得"""
    res = requests.get(fund["url"], headers=HEADERS, timeout=15)
    if res.status_code != 200:
        return None, None

    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")
    text = soup.get_text(separator=" ")

    # 基準日の取得（例: 2026年11月8日 または 11/8）
    date_match = re.search(
        r"基準[価日][額\s]*[（\(：:]\s*([0-9]{4}年)?([0-9]{1,2})月([0-9]{1,2})日",
        text,
    )
    date_str = (
        f"{int(date_match.group(2))}/{int(date_match.group(3))}"
        if date_match
        else ""
    )

    # 基準価額（コロン「:」の有無どちらにも対応）
    price_match = re.search(r"基準価額[:：\s]*([0-9,]+)\s*円", text)
    if not price_match:
        return None, None
    price_int = int(price_match.group(1).replace(",", ""))

    # 前日比(%)（コロン「:」や半角/全角%に対応）
    pct_match = re.search(r"前日比[^\n\r]*?([+-]?[0-9.]+)[\%％]", text)
    daily_pct = float(pct_match.group(1)) if pct_match else 0.0

    # 昨年末比・設定来の計算
    base_price = fund["base_price"]
    diff_pct = ((price_int - base_price) / base_price) * 100

    daily_sign = "+" if daily_pct > 0 else ""
    diff_sign = "+" if diff_pct > 0 else ""

    line = f"・{fund['short_name']} {price_int:,}円 (前日{daily_sign}{daily_pct:.1f}% / {fund['label']}{diff_sign}{diff_pct:.1f}%)"
    print(f"[{fund['short_name']}] 公式から取得成功: {line}")
    return date_str, line


def main():
    fund_lines = []
    latest_date = ""

    # fundnote公式サイトだけを直接巡回
    for fund in TARGET_FUNDS:
        try:
            date_str, line = fetch_from_official_fundnote(fund)
            if line:
                fund_lines.append(line)
                if date_str and not latest_date:
                    latest_date = date_str
        except Exception as e:
            print(f"[{fund['short_name']}] エラー: {e}")

    if not fund_lines:
        print("fundnote公式サイトからデータが取得できませんでした。")
        return

    # 重複投稿防止
    last_date = ""
    if os.path.exists("last_date.txt"):
        with open("last_date.txt", "r", encoding="utf-8") as f:
            last_date = f.read().strip()

    if latest_date and latest_date == last_date:
        print(f"基準日 {latest_date} はすでにツイート済みです。終了します。")
        return

    # ツイート作成
    tweet_text = f"【fundnote】{latest_date}\n" + "\n".join(fund_lines)
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
    if latest_date:
        with open("last_date.txt", "w", encoding="utf-8") as f:
            f.write(latest_date)
    print("fundnote公式の最新基準価額でツイート完了しました！")


if __name__ == "__main__":
    main()
