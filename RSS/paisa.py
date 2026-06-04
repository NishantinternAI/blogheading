import feedparser

def fetch_5paisa():
    url = "https://www.5paisa.com/rss/news.xml"
    feed = feedparser.parse(url)

    data = []

    for entry in feed.entries:
        item = {
            "Blog_Title": entry.get("title", ""),
            "Blog_Links": entry.get("link", ""),
            "Blog_PublishDate": entry.get("published", ""),
            "Blog_Content": entry.get("summary", ""),  # full content
            # "contentSnippet": entry.get("summary", "")[:100],  # short preview
            # "guid": entry.get("id", entry.get("link", "")),
            # "isoDate": entry.get("published", "")
        }

        data.append(item)

    return data
print(len(fetch_5paisa())) # 10
if __name__ == "__main__":
    results = fetch_5paisa()
    print(f"\nTotal: {len(results)}")
    print("=" * 60)
    for r in results:
        print(f"Title   : {r['Blog_Title']}")
        print(f"Link    : {r['Blog_Links']}")
        # print(f"Traffic : {r['traffic']}")
        print(f"Date    : {r['Blog_PublishDate']}")
        print(f"Content : {r['Blog_Content'][:120]}")
        print(f"---")
# print(fetch_5paisa())
