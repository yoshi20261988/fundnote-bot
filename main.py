import os
import re
import requests
from bs4 import BeautifulSoup
import tweepy

# 本物のブラウザと同じヘッダー（ブロック防止）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

TARGET_FUNDS = [
    {
        "short_name": "かいほう",
        "url": "https://www.fundnote.co.jp/fund/kaihou/",
        "full_name": "fundnote日本株Kaihouファンド",
        "base_price": 15392,
        "label": "年末比",
    },
    {
        "short_name": "さいこう",
        "url": "https://www.fundnote.co.jp/fund/saikou/",
        "full_name": "fundnoteTOB企業価値ジャッジファンド",
        "base_price": 10214,
        "label": "年末比",
    },
    {
        "short_name": "だるとん",
        "url": "https://www.fundnote.co.jp/fund/dalton/",
        "full_name": "fundnoteダルトンNAVFセレクトファンド",
        "base_price": 10000,
        "label": "設定来",
    },
    {
        "short_name": "あけぼの",
        "url": "https://www.fundnote.co.jp/fund/akebono/",
        "full_name": "fundnoteIPOクロスオーバーファンド",
        "base_price": 9682,
        "label": "年末比",
    },
    {
        "short_name": "にっぽん",
        "url": "https://www.fundnote.co.jp/fund/nipponbare/",
        "full_name": "fundnoteNVI日本バリューファンド",
        "base_price": 10000,
        "label": "設定来",
    },
]


def fetch_from_individual_page(fund):
    """各ファンドの個別公式ページから取得"""
    res = requests.get(fund["url"], headers=HEADERS, timeout=15)
    print(f"[{fund['short_name']}] 個別ページ取得ステータス: {res.status_code}")
    if res.status_code != 200:
        return None, None

    res.encoding = res.apparent_encoding
    soup = BeautifulSoup(res.text, "html.parser")
    text = soup.get_text()

    # 基準日の取得
    date_match = re.search(
        r"基準[価日][額\s]*[（\(：:]\s*([0-9]{4}年)?([0-9]{1,2})月([0-9]{1,2})日",
        text,
    )
    date_str = (
        f"{int(date_match.group(2))}/{int(date_match.group(3))}"
        if date_match
        else ""
    )

    # 基準価額
    price_match = re.search(r"基準価額\s*[:：]?\s*([0-9,]+)\s*円", text)
    if not price_match:
        return None, None
    price_int = int(price_match.group(1).replace(",", ""))

    # 前日比(%)（半角・全角の両方に対応）
    pct_match = re.search(r"前日比[^\n\r]*?([+-]?[0-9.]+)[\%％]", text)
    daily_pct = float(pct_match.group(1)) if pct_match else 0.0

    # 昨年末比・設定来の計算
    base_price = fund["base_price"]
    diff_pct = ((price_int - base_price) / base_price) * 100

    daily_sign = "+" if daily_pct > 0 else ""
    diff_sign = "+" if diff_pct > 0 else ""

    line = f"・{fund['short_name']} {price_int:,}円 (前日{daily_sign}{daily_pct:.1f}% / {fund['label']}{diff_sign}{diff_pct:.1f}%)"
    return date_str, line


def fetch_from_history_page():
    """公式一覧ページ（base-price-history）からのフォールバック取得"""
    url = "https://www.fundnote.co.jp/base-price-history/"
    res = requests.get(url, headers=HEADERS, timeout=15)
    print(f"[一覧ページ] 取得ステータス: {res.status_code}")
    if res.status_code != 200:
        return "", []

    res.encoding = res.apparent_encoding
    soup = BeautifulSoup(res.text, "html.parser")
    text = soup.get_text()

    date_match = re.search(
        r"基準日[：:]\s*([0-9]{4}年)?([0-9]{1,2})月([0-9]{1,2})日", text
    )
    date_str = (
        f"{int(date_match.group(2))}/{int(date_match.group(3))}"
        if date_match
        else ""
    )

    lines = []
    for fund in TARGET_FUNDS:
        if fund["full_name"] not in text:
            continue
        sub_text = text.split(fund["full_name"])[1][:300]
        price_match = re.search(r"基準価額\s*[:：]?\s*([0-9,]+)\s*円", sub_text)
        pct_match = re.search(r"前日比[^\n\r]*?([+-]?[0-9.]+)[\%％]", sub_text)

        if price_match:
            price_int = int(price_match.group(1).replace(",", ""))
            daily_pct = float(pct_match.group(1)) if pct_match else 0.0

            base_price = fund["base_price"]
            diff_pct = ((price_int - base_price) / base_price) * 100

            daily_sign = "+" if daily_pct > 0 else ""
            diff_sign = "+" if diff_pct > 0 else ""

            line = f"・{fund['short_name']} {price_int:,}円 (前日{daily_sign}{daily_pct:.1f}% / {fund['label']}{diff_sign}{diff_pct:.1f}%)"
            lines.append(line)

    return date_str, lines


def main():
    fund_lines = []
    latest_date = ""

    # 1. まず各個別ページから取得
    for fund in TARGET_FUNDS:
        try:
            date_str, line = fetch_from_individual_page(fund)
            if line:
                fund_lines.append(line)
                if date_str and not latest_date:
                    latest_date = date_str
        except Exception as e:
            print(f"個別ページエラー ({fund['short_name']}): {e}")

    # 2. 個別で取れなかった場合は一覧ページから取得
    if not fund_lines:
        print("個別ページから取得できなかったため、一覧ページから取得します。")
        try:
            latest_date, fund_lines = fetch_from_history_page()
        except Exception as e:
            print(f"一覧ページエラー: {e}")

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

    # 日付を保存
    if latest_date:
        with open("last_date.txt", "w", encoding="utf-8") as f:
            f.write(latest_date)
    print("正常にツイートが完了しました！")


if __name__ == "__main__":
    main()
