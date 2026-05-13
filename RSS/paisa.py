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
# print(fetch_5paisa())
