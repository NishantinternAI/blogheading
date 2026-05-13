import feedparser
from datetime import datetime
def fetch_cnbc():
    url = "https://www.cnbctv18.com/commonfeeds/v1/cne/rss/economy.xml"
    feed = feedparser.parse(url)

    result = []

    for entry in feed.entries:
        item = {
            "Blog_Title": entry.get("title", ""),
            "Blog_Links": entry.get("link", ""),
            "Blog_PublishDate": entry.get("published", ""),
            # "dc:creator": entry.get("author", ""),  # mapped
            "Blog_Content": entry.get("summary", ""),
          
        }

        result.append(item)

    return result
print(len(fetch_cnbc())) # 200
# print(fetch_cnbc())
# for r in result[:2]:   # print first 2 items
#     print(r)