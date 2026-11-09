import os
import re
import requests
from bs4 import BeautifulSoup
import tweepy

API_URL = "https://d31w0dmwtc2au2.cloudfront.net/base-price"
API_KEY = "xW75MMRSbLbUfU5KOru3rlvc8AJFgISc0L"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "x-api-key": API_KEY,
    "Content-Type": "application/json",
}

# 比較用の基準価格
BASE_CONFIG = {
    "かいほう": {"base": 15392, "label": "年末比"},
    "さいこう": {"base": 10214, "label": "年末比"},
    "だるとん": {"base": 10000, "label": "設定来"},
    "あけぼの": {"base": 9682, "label": "年末比"},
    "にっぽん": {"base": 10000, "label": "設定来"},
}


def get_fund_titles():
    """公式サイトのHTMLから正しいファンド名（キー）を抽出"""
    url = "https://www.fundnote.co.jp/base-price-history/"
    res = requests.get(url, headers={"User-Agent": HEADERS["User-Agent"]})
    soup = BeautifulSoup(res.text, "html.parser")

    funds = {}
    # data-fund 属性やクラスからファンド名を自動検出
    for el in soup.find_all(attrs={"data-fund": True}):
        f = el.get("data-fund")
        funds[f] = f

    # 見つからない場合のフォールバック（代表的な正式名称）
    if not funds:
        funds = {
            "fundnote日本株Kaihouファンド": "かいほう",
            "fundnoteTOB企業価値ジャッジファンド": "さいこう",
            "fundnoteダルトンNAVFセレクトファンド": "だるとん",
            "fundnoteIPOクロスオーバーファンド": "あけぼの",
            "fundnoteNVI日本バリューファンド": "にっぽん",
        }
    return funds


def main():
    funds_map = get_fund_titles()
    fund_lines = []
    latest_date = ""

    print("--- fundnote公式APIからデータ取得中 ---")

    for title, short_candidate in funds_map.items():
        try:
            # 公式APIから生JSONを直接取得
            res = requests.get(
                f"{API_URL}?fund={requests.utils.quote(title)}",
                headers=HEADERS,
                timeout=10,
            )
            print(f"[{title}] APIステータス: {res.status_code}")
            if res.status_code != 200:
                continue

            data = res.json()
            # active なエントリ（最新データ）を取得
            active_item = None
            if isinstance(data, list):
                for item in data:
                    if item.get("active") is True:
                        active_item = item
                        break
                if not active_item and len(data) > 0:
                    active_item = data[0]
            elif isinstance(data, dict):
                active_item = data

            if not active_item:
                print(f"[{title}] データなし")
                continue

            print(f"[{title}] 取得生データ: {active_item}")

            # 略称の判定
            short_name = ""
            if "Kaihou" in title or "かいほう" in title:
                short_name = "かいほう"
            elif "TOB" in title or "さいこう" in title:
                short_name = "さいこう"
            elif "ダルトン" in title or "だるとん" in title:
                short_name = "だるとん"
            elif "IPO" in title or "あけぼの" in title:
                short_name = "あけぼの"
            elif "NVI" in title or "にっぽん" in title:
                short_name = "にっぽん"
            else:
                short_name = short_candidate

            # 金額・前日比・日付の取り出し
            # APIの一般的なフィールド名（basePrice, diff, ratio, date等）に対応
            price = (
                active_item.get("basePrice")
                or active_item.get("price")
                or active_item.get("base_price")
            )
            pct = (
                active_item.get("ratio")
                or active_item.get("diffRatio")
                or active_item.get("diff_ratio")
                or active_item.get("diff_percent")
            )
            date_val = active_item.get("date") or active_item.get("baseDate")

            if price is None:
                continue

            price_int = int(str(price).replace(",", "").split(".")[0])
            daily_pct = float(pct) if pct is not None else 0.0

            # 日付フォーマット（例: 2026-11-08 → 11/8）
            if date_val and not latest_date:
                d_m = re.search(r"([0-9]{1,2})[-/月]([0-9]{1,2})", str(date_val))
                if d_m:
                    latest_date = f"{int(d_m.group(1))}/{int(d_m.group(2))}"

            # 昨年末比・設定来の計算
            config = BASE_CONFIG.get(
                short_name, {"base": 10000, "label": "設定来"}
            )
            diff_pct = ((price_int - config["base"]) / config["base"]) * 100

            daily_sign = "+" if daily_pct > 0 else ""
            diff_sign = "+" if diff_pct > 0 else ""

            line = f"・{short_name} {price_int:,}円 (前日{daily_sign}{daily_pct:.1f}% / {config['label']}{diff_sign}{diff_pct:.1f}%)"
            fund_lines.append(line)

        except Exception as e:
            print(f"[{title}] 取得エラー: {e}")

    if not fund_lines:
        print("APIからのデータ取得に失敗しました。")
        return

    # 日付が取れなかった場合のフォールバック
    if not latest_date:
        latest_date = "最新"

    # 重複投稿防止
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

    if latest_date != "最新":
        with open("last_date.txt", "w", encoding="utf-8") as f:
            f.write(latest_date)
    print("fundnote公式API直結でツイート完了しました！")


if __name__ == "__main__":
    main()
