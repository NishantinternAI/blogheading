import feedparser
from datetime import datetime

def fetch_livemint():
    url = "https://www.livemint.com/rss/news"
    feed = feedparser.parse(url)

    data = []

    for entry in feed.entries:
        item = {
            "Blog_Title": entry.get("title", ""),
            "Blog_Links": entry.get("link", ""),
            "Blog_PublishDate": entry.get("published", ""),
            "Blog_Content": "",
            # "contentSnippet": entry.get("summary", ""),
            # "guid": entry.get("id", entry.get("link", "")),
            # "isoDate": ""
        }

        # Extract content (if available)
        if "content" in entry:
            item["content"] = entry.content[0].value
        else:
            item["content"] = entry.get("summary", "")

        # Convert to ISO Date
        if "published_parsed" in entry and entry.published_parsed:
            item["isoDate"] = datetime(*entry.published_parsed[:6]).isoformat()

        data.append(item)

    return data
print(len(fetch_livemint()))  #35
