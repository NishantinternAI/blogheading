import requests
import datetime
from dotenv import load_dotenv
import os

load_dotenv()
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")


def fetch_finnhub_news(category: str = "general",
                        top_n: int   = 10) -> list:
    """
    Fetches market news from Finnhub.
    Free tier: 60 calls/minute.

    category options:
      general, forex, crypto, merger
    """
    url = "https://finnhub.io/api/v1/news"

    params = {
        "category": category,
        "token":    FINNHUB_KEY,
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        items = resp.json()

        articles = []
        print(f"[FH] {len(items)} raw articles")

        for item in items[:top_n]:
            title    = item.get("headline", "").strip()
            link     = item.get("url",      "").strip()
            summary  = item.get("summary",  "").strip()
            source   = item.get("source",   "").strip()
            image    = item.get("image",    "").strip()
            category = item.get("category", "").strip()

            # ── Convert Unix timestamp to readable date ────────
            ts        = item.get("datetime", 0)
            published = datetime.datetime.fromtimestamp(ts).strftime(
                "%a, %d %b %Y %H:%M:%S +0530"
            ) if ts else ""

            if not title or not summary:
                continue

            articles.append({
                "Blog_Title":       title,
                "Blog_Links":       link,
                "Blog_PublishDate": published,
                "Blog_Content":     summary,
                "source":           "finnhub",
                "source_name":      f"Finnhub ({source})",
                "_source_type":     "news",
                "_content_words":   len(summary.split()),
                "_content_quality": "rich" if len(summary.split()) >= 300
                                    else "thin" if len(summary.split()) >= 150
                                    else "bare",
                "_category":        category,
                "_image":           image,
            })

        print(f"[FH] Valid: {len(articles)}")
        return articles

    except Exception as e:
        print(f"[FH] Error: {e}")
        return []


def fetch_finnhub_company_news(symbol:   str = "RELIANCE.NS",
                                from_date: str = "",
                                to_date:   str = "",
                                top_n:     int = 10) -> list:
    """
    Fetches news for a specific stock symbol.

    symbol examples:
      Indian stocks : RELIANCE.NS, TCS.NS, HDFCBANK.NS
      US stocks     : AAPL, TSLA, GOOGL
    """
    url = "https://finnhub.io/api/v1/company-news"

    # Default to last 7 days if no dates provided
    if not to_date:
        to_date = datetime.date.today().strftime("%Y-%m-%d")
    if not from_date:
        from_date = (
            datetime.date.today() - datetime.timedelta(days=7)
        ).strftime("%Y-%m-%d")

    params = {
        "symbol": symbol,
        "from":   from_date,
        "to":     to_date,
        "token":  FINNHUB_KEY,
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        items = resp.json()

        articles = []
        print(f"[FH] {len(items)} articles for {symbol}")

        for item in items[:top_n]:
            title   = item.get("headline", "").strip()
            link    = item.get("url",      "").strip()
            summary = item.get("summary",  "").strip()
            source  = item.get("source",   "").strip()

            ts        = item.get("datetime", 0)
            published = datetime.datetime.fromtimestamp(ts).strftime(
                "%a, %d %b %Y %H:%M:%S +0530"
            ) if ts else ""

            if not title or not summary:
                continue

            articles.append({
                "Blog_Title":       title,
                "Blog_Links":       link,
                "Blog_PublishDate": published,
                "Blog_Content":     summary,
                "source":           "finnhub",
                "source_name":      f"Finnhub ({source})",
                "_source_type":     "news",
                "_symbol":          symbol,
                "_content_words":   len(summary.split()),
            })

        print(f"[FH] Valid: {len(articles)}")
        return articles

    except Exception as e:
        print(f"[FH] Error: {e}")
        return []


if __name__ == "__main__":
    print("=" * 60)
    print("  Finnhub News Fetcher")
    print("=" * 60)

    # ── General market news ───────────────────────────────────
    print("\n── General Market News ──")
    results = fetch_finnhub_news(category="general", top_n=5)
    for i, r in enumerate(results, 1):
        print(f"[{i}] {r['Blog_Title'][:70]}")
        print(f"     {r['Blog_PublishDate']}")
        print(f"     {r['Blog_Content'][:150]}...")

    # ── Merger news ───────────────────────────────────────────
    print("\n── Merger News ──")
    mergers = fetch_finnhub_news(category="merger", top_n=5)
    for i, r in enumerate(mergers, 1):
        print(f"[{i}] {r['Blog_Title'][:70]}")

    # ── Company specific news ─────────────────────────────────
    print("\n── Reliance Industries News ──")
    reliance = fetch_finnhub_company_news(
        symbol    = "RELIANCE.NS",
        top_n     = 5
    )
    for i, r in enumerate(reliance, 1):
        print(f"[{i}] {r['Blog_Title'][:70]}")