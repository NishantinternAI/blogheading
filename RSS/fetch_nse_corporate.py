
import feedparser
import requests

def fetch_nse_corporate():
    url = "https://nsearchives.nseindia.com/content/RSS/Corporate_action.xml"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/xml"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print("Failed to fetch RSS:", response.status_code)
        return []

    feed = feedparser.parse(response.content)

    print("Entries found:", len(feed.entries))  # debug

    data = []

    for entry in feed.entries:
        item = {
            "Blog_Title": entry.get("title", "").strip(),
            "Blog_Link": entry.get("link", "").strip(),
            "Blog_PublishDate": entry.get("published", "").strip(),
            "Blog_Content": entry.get("summary", "").strip(),
            "Source": "NSE Corporate Actions",
            "Detected_Country": "India"
        }
        data.append(item)

    print(f"[INFO] NSE Corporate fetched: {len(data)}")
    return data


# Test
result = fetch_nse_corporate()
print("NSE COUNT:", len(result))
