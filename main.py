import os
import re
import requests
from bs4 import BeautifulSoup
import tweepy

# 各ファンドの公式サイト個別ページと基準価格
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


def fetch_fund_info(fund):
    """各ファンドの個別ページから最新データを取得"""
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(fund["url"], headers=headers, timeout=10)
    res.encoding = res.apparent_encoding
    soup = BeautifulSoup(res.text, "html.parser")
    text = soup.get_text()

    # 基準日の取得
    date_match = re.search(
        r"基準価額[（\(]\s*[0-9]{4}年([0-9]{1,2})月([0-9]{1,2})日\s*[）\)]", text
    )
    # 基準価額の取得
    price_match = re.search(r"基準価額\s*([0-9,]+)円", text)
    # 前日比(%)の取得
    pct_match = re.search(r"前日比.*?（?([+-]?[0-9.]+)％?\)?", text)

    if not price_match or not pct_match:
        return None, None

    date_str = (
        f"{int(date_match.group(1))}/{int(date_match.group(2))}"
        if date_match
        else ""
    )
    price_int = int(price_match.group(1).replace(",", ""))
    daily_pct = float(pct_match.group(1))

    # 昨年末比または設定来の計算
    base_price = fund["base_price"]
    diff_pct = ((price_int - base_price) / base_price) * 100

    daily_sign = "+" if daily_pct > 0 else ""
    diff_sign = "+" if diff_pct > 0 else ""

    line = f"・{fund['short_name']} {price_int:,}円 (前日{daily_sign}{daily_pct:.1f}% / {fund['label']}{diff_sign}{diff_pct:.1f}%)"
    return date_str, line


def main():
    fund_lines = []
    latest_date = ""

    for fund in TARGET_FUNDS:
        try:
            date_str, line = fetch_fund_info(fund)
            if line:
                fund_lines.append(line)
                if date_str and not latest_date:
                    latest_date = date_str
        except Exception as e:
            print(f"{fund['short_name']} の取得エラー: {e}")

    if not fund_lines:
        print("データが取得できませんでした。")
        return

    # 前回投稿日との重複チェック
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

    # 投稿成功した日付を記録
    if latest_date:
        with open("last_date.txt", "w", encoding="utf-8") as f:
            f.write(latest_date)
    print("正常にツイートが完了しました！")


if __name__ == "__main__":
    main()
