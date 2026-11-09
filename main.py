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
        "base_price": 15392,
        "label": "年末比",
    },
    {
        "short_name": "さいこう",
        "keyword": "TOB",
        "base_price": 10214,
        "label": "年末比",
    },
    {
        "short_name": "だるとん",
        "keyword": "ダルトン",
        "base_price": 10000,
        "label": "設定来",
    },
    {
        "short_name": "あけぼの",
        "keyword": "IPO",
        "base_price": 9682,
        "label": "年末比",
    },
    {
        "short_name": "にっぽん",
        "keyword": "NVI",
        "base_price": 10000,
        "label": "設定来",
    },
]


def main():
    # 毎日夕方に全ファンドが更新される公式の基準価額一覧ページを取得
    url = "https://www.fundnote.co.jp/base-price-history/"
    res = requests.get(url, headers=HEADERS, timeout=15)
    res.encoding = "utf-8"
    print(f"[公式一覧ページ] 取得ステータス: {res.status_code}")

    if res.status_code != 200:
        print("公式サイトへのアクセスに失敗しました。")
        return

    # HTMLタグを除去してテキストだけをクリーンに抽出
    soup = BeautifulSoup(res.text, "html.parser")
    clean_text = " ".join(soup.get_text().split())

    # 基準日の取得（例: 11/8）
    d_m = re.search(
        r"基準日[：:]\s*([0-9]{4}年)?\s*([0-9]{1,2})月([0-9]{1,2})日",
        clean_text,
    )
    latest_date = (
        f"{int(d_m.group(2))}/{int(d_m.group(3))}" if d_m else "最新"
    )
    print(f"基準日: {latest_date}")

    fund_lines = []
    for t in TARGETS:
        if t["keyword"] in clean_text:
            sub = clean_text.split(t["keyword"])[1][:400]
            p_m = re.search(r"基準価額[:：\s]*([0-9,]+)\s*円", sub)
            pct_m = re.search(r"前日比.*?([+-]?[0-9.]+)[\%％]", sub)

            if p_m:
                price_int = int(p_m.group(1).replace(",", ""))
                daily_pct = float(pct_m.group(1)) if pct_m else 0.0

                # 昨年末比・設定来の計算
                diff_pct = ((price_int - t["base_price"]) / t["base_price"]) * 100
                daily_sign = "+" if daily_pct > 0 else ""
                diff_sign = "+" if diff_pct > 0 else ""

                short_name = t["short_name"]
                label = t["label"]
                line = f"・{short_name} {price_int:,}円 (前日{daily_sign}{daily_pct:.1f}% / {label}{diff_sign}{diff_pct:.1f}%)"
                fund_lines.append(line)
                print(f"[{short_name}] 取得成功: {line}")
            else:
                print(f"[{t['short_name']}] 準備中または未公表のためスキップ")

    if not fund_lines:
        print("ファンドのデータが取得できませんでした。")
        return

    # 重複投稿防止チェック
    last_date = ""
    if os.path.exists("last_date.txt"):
        with open("last_date.txt", "r", encoding="utf-8") as f:
            last_date = f.read().strip()

    if latest_date != "最新" and latest_date == last_date:
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

    # 日付を保存
    if latest_date != "最新":
        with open("last_date.txt", "w", encoding="utf-8") as f:
            f.write(latest_date)
    print("fundnote公式の最新基準価額でツイート完了しました！")


if __name__ == "__main__":
    main()
