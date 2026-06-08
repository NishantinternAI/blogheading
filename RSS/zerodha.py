# import feedparser

# def fetch_zerodha():
#     url = "https://pulse.zerodha.com/feed.php"
#     feed = feedparser.parse(url)

#     data = []

#     for entry in feed.entries:
#         item = {
#             "Blog_Title": entry.get("title", ""),
#             "Blog_Link": entry.get("link", ""),
            
#             # Handle content safely
#             "Blog_Content": (
#                 entry.get("content", [{}])[0].get("value", "")
#                 if "content" in entry
#                 else entry.get("summary", "")
#             ),

#             # Handle date safely
#             "Publish_Date": (
#                 entry.get("published") or
#                 entry.get("updated") or
#                 "Not Available"
#             ),

#             # ISO Date (your Is_Date)
#             "Is_Date": entry.get("updated", "")
#         }

#         data.append(item)

#     return data


# print(len(fetch_zerodha())) # 25


# RSS/zerodha.py

import feedparser


ZERODHA_FEED_URL = "https://pulse.zerodha.com/feed.php"


def fetch_zerodha() -> list:
    """
    Fetches articles from Zerodha Pulse RSS feed.
    Uses consistent field names matching rest of pipeline.
    """
    print(f"[ZERODHA] Fetching Zerodha Pulse...")

    feed = feedparser.parse(ZERODHA_FEED_URL)
    data = []

    for entry in feed.entries:
        title = entry.get("title", "").strip()

        if not title:
            continue

        # ── Get content ────────────────────────────────────────
        content = ""
        if "content" in entry and entry["content"]:
            content = entry["content"][0].get("value", "")
        if not content:
            content = entry.get("summary", "")

        # ── Get date ───────────────────────────────────────────
        pub_date = (
            entry.get("published") or
            entry.get("updated")   or
            ""
        )

        # ── Use Blog_PublishDate (consistent with pipeline) ────
        data.append({
            "Blog_Title":       title,
            "Blog_Links":       entry.get("link", ""),   # Blog_Links not Blog_Link
            "Blog_Content":     content,
            "Blog_PublishDate": pub_date,                # consistent field name
            "source_name":      "Zerodha Pulse",
        })

    print(f"[ZERODHA] Total: {len(data)}")
    return data


if __name__ == "__main__":
    results = fetch_zerodha()
    print(f"Total: {len(results)}")
    for i, r in enumerate(results[:5], 1):
        print(f"\n[{i}] Title : {r['Blog_Title']}")
        print(f"    Date  : {r['Blog_PublishDate']}")
        print(f"    Link  : {r['Blog_Links'][:70]}")