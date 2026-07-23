# """
# add_keywords_first_50_only.py

# Reads output.json (a list of blog article dicts), takes the FIRST 50 blogs,
# runs extract_keywords() on each blog's content (skipping any that already
# have keywords), writes primary_keyword / secondary_keywords back into each
# blog dict, and saves ONLY those 50 blogs (not the full original list) to a
# new JSON file.
# """

# import json
# from core.model_client import cached_model_call

# INPUT_FILE = r"D:\Blogheading\output\output.json"
# OUTPUT_FILE = r"D:\Blogheading\output\output_first50_with_keywords.json"
# NUM_BLOGS_TO_PROCESS = 50


# def extract_keywords(article_content: str) -> dict:
#     prompt = f"""
# You are an SEO keyword researcher for an Indian stock market blog.

# Analyze the article below and extract keywords that real investors
# actually type into Google Search — not news headlines.

# RULES FOR PRIMARY KEYWORD:
# - Maximum 4 words
# - Must be a real search query, not an article title
# - Format: [Company Name] + [action]  e.g. "IRFC share price"
# - Pick the SINGLE most searched company or topic in the article
# - No dates, no percentages, no rupee amounts

# RULES FOR SECONDARY KEYWORDS:
# - Maximum 6 keywords total
# - Each keyword: 2 to 5 words only
# - No dates  (not "June 2026", not "Q1 FY26")
# - No percentages  (not "2% stake", not "58% acquisition")
# - No rupee amounts  (not "₹91 floor price")
# - Format: [Company] + [generic action]  e.g. "IRFC OFS", "Infosys stock"
# - Think: what would an investor search BEFORE reading this news

# GOOD EXAMPLES:
#   primary_keyword    : "IRFC share price"
#   secondary_keywords : ["IRFC OFS", "Infosys stock NSE",
#                         "City Union Bank dividend",
#                         "Honasa Consumer stock",
#                         "Rashi Peripherals acquisition"]

# BAD EXAMPLES — never return these:
#   "Stocks In Focus Today: Infosys, IRFC..."   ← article title, not a search query
#   "IRFC divestment 2% stake June 24 25 2026"  ← too specific, zero search volume
#   "IRFC OFS floor price ₹91"                  ← has rupee amount

# Return ONLY valid JSON. No markdown. No explanation.

# {{
#   "primary_keyword": "",
#   "secondary_keywords": []
# }}

# ARTICLE:
# {article_content}
# """

#     try:
#         result = cached_model_call(prompt)
#         return json.loads(result)
#     except Exception:
#         return {
#             "primary_keyword": "",
#             "secondary_keywords": []
#         }


# def get_article_content(article: dict) -> str:
#     """
#     Prefer the generated blog content (article['blog']['Blog_Content']) since
#     that's the SEO-optimized version. Fall back to the raw scraped content.
#     """
#     blog = article.get("blog") or {}
#     content = blog.get("Blog_Content") or article.get("Blog_Content") or ""
#     title = blog.get("Blog_Title") or article.get("Blog_Title") or ""
#     return f"{title}\n\n{content}".strip()


# def has_keywords(article: dict) -> bool:
#     pk = article.get("primary_keyword")
#     sk = article.get("secondary_keywords")
#     return bool(pk) and bool(sk)


# def main():
#     with open(INPUT_FILE, "r", encoding="utf-8") as f:
#         articles = json.load(f)

#     # Take exactly the first 50 blogs — this is the ONLY slice we work with.
#     first_50 = articles[:NUM_BLOGS_TO_PROCESS]

#     for i, article in enumerate(first_50):
#         if has_keywords(article):
#             print(f"[{i+1}/{len(first_50)}] Already has keywords, skipping.")
#             continue

#         content = get_article_content(article)
#         keywords = extract_keywords(content)

#         article["primary_keyword"] = keywords.get("primary_keyword", "")
#         article["secondary_keywords"] = keywords.get("secondary_keywords", [])

#         print(f"[{i+1}/{len(first_50)}] Primary: {article['primary_keyword']}")
#         print(f"           Secondary: {article['secondary_keywords']}")

#     # Save ONLY the 50 processed blogs — NOT the full 996-blog list.
#     with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
#         json.dump(first_50, f, ensure_ascii=False, indent=4)

#     print(f"\nSaved {len(first_50)} blogs to {OUTPUT_FILE}")


# if __name__ == "__main__":
#     main()



"""
add_missing_keywords.py

Reads output.json,
Starts from the LAST blog,
Checks blogs between Today and 22 June 2026,
Generates keywords only if missing,
Saves ONLY processed blogs into another JSON file.
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root, for add_cached
from core.model_client import cached_model_call

INPUT_FILE = r"D:\Blogheading\output\output.json"
OUTPUT_FILE = r"D:\Blogheading\output\blogs_missing_keywords.json"

# Process blogs from today back to this date
START_DATE = datetime(2026, 6, 22)


def extract_keywords(article_content: str) -> dict:
    prompt = f"""
You are an SEO keyword researcher for an Indian stock market blog.

Analyze the article below and extract keywords that real investors
actually type into Google Search — not news headlines.

RULES FOR PRIMARY KEYWORD:
- Maximum 4 words
- Must be a real search query
- Format: Company + Action
- Example: "IRFC share price"
- Pick only ONE keyword

RULES FOR SECONDARY KEYWORDS:
- Maximum 6 keywords
- Each keyword: 2-5 words
- No dates
- No percentages
- No rupee amounts

Return ONLY valid JSON.

{{
    "primary_keyword": "",
    "secondary_keywords": []
}}

ARTICLE:
{article_content}
"""

    try:
        response = cached_model_call(prompt)
        return json.loads(response)

    except Exception as e:
        print("Keyword extraction failed:", e)
        return {
            "primary_keyword": "",
            "secondary_keywords": []
        }


def get_article_content(article: dict) -> str:
    blog = article.get("blog", {})

    title = (
        blog.get("Blog_Title")
        or article.get("Blog_Title")
        or ""
    )

    content = (
        blog.get("Blog_Content")
        or article.get("Blog_Content")
        or ""
    )

    return f"{title}\n\n{content}".strip()


def has_keywords(article: dict) -> bool:
    """
    Returns True if article already has keywords.
    Supports both old string format and new dictionary format.
    """

    pk = article.get("primary_keyword")
    sk = article.get("secondary_keywords")

    # Primary keyword check
    if not pk:
        return False

    if isinstance(pk, dict):
        if not pk.get("google_keyword"):
            return False

    elif isinstance(pk, str):
        if pk.strip() == "":
            return False

    # Secondary keyword check
    if not sk:
        return False

    if isinstance(sk, list) and len(sk) == 0:
        return False

    return True


def parse_publish_date(article: dict):
    """
    Converts:
    Mon, 06 Jul 2026 09:58:58 +0530

    into datetime object.
    """

    try:
        date_str = article.get("Blog_PublishDate", "")

        return datetime.strptime(
            date_str,
            "%a, %d %b %Y %H:%M:%S %z"
        ).replace(tzinfo=None)

    except Exception:
        return None


def main():

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        articles = json.load(f)

    recent_blogs = []

    total_checked = 0
    generated = 0
    skipped = 0
    failed = 0

    print("=" * 80)
    print("Reading output.json...")
    print(f"Total blogs in file : {len(articles)}")
    print("=" * 80)

    # Process from LAST blog
    for article in reversed(articles):

        publish_date = parse_publish_date(article)

        if publish_date is None:
            continue

        # Stop once blogs are older than 22 Jun 2026
        if publish_date < START_DATE:
            print("\nReached blogs older than 22 Jun 2026.")
            print("Stopping...")
            break

        total_checked += 1

        title = (
            article.get("blog", {}).get("Blog_Title")
            or article.get("Blog_Title")
            or "Untitled"
        )

        print("\n" + "-" * 80)
        print(f"[{total_checked}]")
        print(f"Title      : {title}")
        print(f"Published  : {publish_date.strftime('%d %b %Y')}")

        try:

            if has_keywords(article):

                skipped += 1

                print("Status     : Keywords already exist")

                pk = article.get("primary_keyword")

                if isinstance(pk, dict):
                    print("Primary    :", pk.get("google_keyword", ""))
                else:
                    print("Primary    :", pk)

            else:

                generated += 1

                print("Status     : Missing keywords")
                print("Generating keywords...")

                content = get_article_content(article)

                keywords = extract_keywords(content)

                article["primary_keyword"] = keywords.get(
                    "primary_keyword",
                    ""
                )

                article["secondary_keywords"] = keywords.get(
                    "secondary_keywords",
                    []
                )

                print("\n✓ Keywords Generated")

                print("Primary Keyword:")
                print(article["primary_keyword"])

                print("\nSecondary Keywords:")
                print(article["secondary_keywords"])

        except Exception as e:

            failed += 1

            print("Error :", e)

        # VERY IMPORTANT
        # Save EVERY blog in this date range,
        # whether keywords existed or were generated.
        recent_blogs.append(article)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            recent_blogs,
            f,
            ensure_ascii=False,
            indent=4
        )

    print("\n")
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Blogs Checked            : {total_checked}")
    print(f"Already Had Keywords     : {skipped}")
    print(f"Keywords Generated       : {generated}")
    print(f"Failed                   : {failed}")
    print(f"Saved Blogs              : {len(recent_blogs)}")
    print()
    print("Output File")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()