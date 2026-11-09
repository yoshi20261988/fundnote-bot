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

# fundnote公式サイトの対象ファンド設定
TARGETS = [
    {
        "short_name": "かいほう",
        "keyword": "Kaihou",
        "slug": "kaihou",
        "base_price": 15392,
        "label": "年末比",
    },
    {
        "short_name": "さいこう",
        "keyword": "TOB",
        "slug": "saikou",
        "base_price": 10214,
        "label": "年末比",
    },
    {
        "short_name": "だるとん",
        "keyword": "ダルトン",
        "slug": "dalton",
        "base_price": 10000,
        "label": "設定来",
    },
    {
        "short_name": "あけぼの",
        "keyword": "IPO",
        "slug": "akebono",
        "base_price": 9682,
        "label": "年末比",
    },
    {
        "short_name": "にっぽん",
        "keyword": "NVI",
        "slug": "nipponbare",
        "base_price": 10000,
        "label": "設定来",
    },
]


def parse_fund_data(text, base_price, label, short_name):
    # 基準価額
    price_match = re.search(r"基準価額[:：\s]*([0-9,]+)\s*円", text)
    if not price_match:
        return None
    price_int = int(price_match.group(1).replace(",", ""))

    # 前日比(%)
    pct_match = re.search(r"前日比[^\n\r]*?([+-]?[0-9.]+)[\%％]", text)
    if not pct_match:
        pct_match = re.search(r"([+-]?[0-9.]+)[\%％]", text)
    daily_pct = float(pct_match.group(1)) if pct_match else 0.0

    # 昨年末比・設定来の計算
    diff_pct = ((price_int - base_price) / base_price) * 100
    daily_sign = "+" if daily_pct > 0 else ""
    diff_sign = "+" if diff_pct > 0 else ""

    line = f"・{short_name} {price_int:,}円 (前日{daily_sign}{daily_pct:.1f}% / {label}{diff_sign}{diff_pct:.1f}%)"
    return line


def main():
    fund_lines = []
    latest_date = ""

    # 1. まず公式の基準価額一覧ページ（毎日夕方に全ファンドが更新されるページ）を取得
    url_history = "https://www.fundnote.co.jp/base-price-history/"
    try:
        res = requests.get(url_history, headers=HEADERS, timeout=15)
        res.encoding = "utf-8"
        text = res.text
        print(f"[公式一覧ページ] 取得ステータス: {res.status_code}")

        # 基準日（例: 11/8）
        d_m = re.search(
            r"基準日[：:]\s*([0-9]{4}年)?([0-9]{1,2})月([0-9]{1,2})日", text
        )
        if d_m:
            latest_date = f"{int(d_m.group(2))}/{int(d_m.group(3))}"
            print(f"基準日を検出: {latest_date}")

        for target in TARGETS:
            if target["keyword"] in text:
                sub = text.split(target["keyword"])[1][:400]
                line = parse_fund_data(
                    sub,
                    target["base_price"],
                    target["label"],
                    target["short_name"],
                )
                if line:
                    fund_lines.append(line)
                    print(f"[{target['short_name']}] 取得成功: {line}")
    except Exception as e:
        print(f"一覧ページ取得エラー: {e}")

    # 2. 一覧ページで取れなかったファンドがあれば個別ページから補完
    if len(fund_lines) < len(TARGETS):
        for target in TARGETS:
            if any(target["short_name"] in l for l in fund_lines):
                continue
            try:
                url_ind = f"https://www.fundnote.co.jp/fund/{target['slug']}/"
                res_ind = requests.get(url_ind, headers=HEADERS, timeout=15)
                res_ind.encoding = "utf-8"
                text_ind = res_ind.text
                line = parse_fund_data(
                    text_ind,
                    target["base_price"],
                    target["label"],
                    target["short_name"],
                )
                if line:
                    fund_lines.append(line)
                    print(
                        f"[{target['short_name']}] 個別ページから取得成功: {line}"
                    )
                    if not latest_date:
                        d_ind = re.search(
                            r"基準[価日][額\s]*[（\(：:]\s*([0-9]{4}年)?([0-9]{1,2})月([0-9]{1,2})日",
                            text_ind,
                        )
                        if d_ind:
                            latest_date = (
                                f"{int(d_ind.group(2))}/{int(d_ind.group(3))}"
                            )
            except Exception as e:
                print(f"[{target['short_name']}] 個別ページ取得エラー: {e}")

    if not fund_lines:
        print("fundnote公式サイトからデータが取得できませんでした。")
        return

    # 重複投稿防止チェック
    last_date = ""
    if os.path.exists("last_date.txt"):
        with open("last_date.txt", "r", encoding="utf-8") as f:
            last_date = f.read().strip()

    if latest_date and latest_date == last_date:
        print(f"基準日 {latest_date} はすでにツイート済みです。終了します。")
        return

    # ツイート作成
    tweet_text = f"【fundnote】{latest_date}\n" + "\n".join(fund_lines)
    print("--- 投稿プレビュー ---\n" + tweet_text)

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
    print("fundnote公式の最新基準価額でツイート完了しました！")


if __name__ == "__main__":
    main()
