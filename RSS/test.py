# RSS/test.py
import feedparser
import requests

feeds = [
    # Zee Business
    "https://www.zeebiz.com/rss",
    "https://www.zeebiz.com/markets/rss",
    "https://www.zeebiz.com/personal-finance/rss",
    "https://www.zeebiz.com/companies/rss",

    # India Infoline
    "https://www.indiainfoline.com/rss",
    "https://www.indiainfoline.com/markets/news/rss",
    "https://www.indiainfoline.com/news/rss",
    "https://www.indiainfoline.com/article/rss",

    # DSIJ
    "https://www.dsij.in/rss",
    "https://www.dsij.in/feeds",
    "https://www.dsij.in/rss/latestnews",
    "https://www.dsij.in/rss/stocknews",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, */*",
}

for url in feeds:
    try:
        r       = requests.get(url, headers=headers, timeout=8)
        feed    = feedparser.parse(r.text)
        entries = len(feed.entries)

        if entries > 0:
            latest  = feed.entries[0].get("published", "N/A")
            title   = feed.entries[0].get("title",     "")[:55]
            summary = feed.entries[0].get("summary",   "")[:80]
            print(f"✅ [{r.status_code}] {entries:>2} entries | {latest}")
            print(f"   URL     : {url}")
            print(f"   Title   : {title}")
            print(f"   Summary : {summary}")
            print()
        else:
            print(f"❌ [{r.status_code}] 0 entries → {url}")

    except Exception as e:
        print(f"❌ FAIL → {url} : {e}")