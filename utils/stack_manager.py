import json
import os
import random
from datetime import datetime
from email.utils import parsedate_to_datetime  # ✅ Parses RSS date format

STACK_FILE = "output/article_stack.json"

def save_stack(articles, created_at=None):
    os.makedirs("output", exist_ok=True)
    with open(STACK_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "created_at": created_at or datetime.now().isoformat(),
            "articles": articles
        }, f, indent=2)
    print(f"[STACK] Saved {len(articles)} articles")

def load_stack():
    if not os.path.exists(STACK_FILE):
        return None, []
    with open(STACK_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("created_at"), data.get("articles", [])

def pop_from_stack():
    created_at, articles = load_stack()
    if not articles:
        return None, None
    article = random.choice(articles)
    articles.remove(article)
    with open(STACK_FILE, "w", encoding="utf-8") as f:
        json.dump({"created_at": created_at, "articles": articles}, f, indent=2)
    print(f"[STACK] Popped. Remaining: {len(articles)}")
    return created_at, article

def get_stack_size():
    _, articles = load_stack()
    return len(articles)

def is_after_morning(article, morning_time_str):
    """
    Check if article Publish_Date is AFTER 9:00 AM morning fetch time
    Handles RSS date format: 'Mon, 04 May 2026 10:27:17 +0530'
    """
    try:
        publish_date_str = article.get("Publish_Date", "")
        if not publish_date_str:
            return False

        # ✅ Parse RSS date format automatically
        article_time = parsedate_to_datetime(publish_date_str)

        # ✅ Parse morning fetch time
        morning_time = datetime.fromisoformat(morning_time_str)

        # ✅ Make both timezone-aware for comparison
        if morning_time.tzinfo is None:
            from datetime import timezone
            morning_time = morning_time.replace(tzinfo=timezone.utc)

        return article_time > morning_time

    except Exception as e:
        print(f"[WARN] Date parse failed: {e}")
        return False