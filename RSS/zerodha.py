import feedparser

def fetch_zerodha():
    url = "https://pulse.zerodha.com/feed.php"
    feed = feedparser.parse(url)

    data = []

    for entry in feed.entries:
        item = {
            "Blog_Title": entry.get("title", ""),
            "Blog_Link": entry.get("link", ""),
            
            # Handle content safely
            "Blog_Content": (
                entry.get("content", [{}])[0].get("value", "")
                if "content" in entry
                else entry.get("summary", "")
            ),

            # Handle date safely
            "Publish_Date": (
                entry.get("published") or
                entry.get("updated") or
                "Not Available"
            ),

            # ISO Date (your Is_Date)
            "Is_Date": entry.get("updated", "")
        }

        data.append(item)

    return data


print(len(fetch_zerodha())) # 25


