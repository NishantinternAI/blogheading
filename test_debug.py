import sys
sys.path.insert(0, ".")

from utils.mcp_tools import fetch_and_clean

url   = "https://www.business-standard.com/markets/capital-market-news/turtlemint-fintech-solutions-ipo-subscribed-45-126061900946_1.html"
title = "Can Amber Challenge Dixon? Brokerages Raise Targets After Oppo Deal Lifts Outlook"

# strip URL fragment before scraping
clean_url = url.split("#")[0]

print(f"URL   : {clean_url}")
print(f"Title : {title}\n")

result = fetch_and_clean(url=clean_url, title=title)

print(f"Method  : {result['method']}")
print(f"Quality : {result['quality']} ({result['word_count']} words)")
print(f"\nContent:")
print("-" * 60)
print(result["content"] if result["content"] else "NO CONTENT")