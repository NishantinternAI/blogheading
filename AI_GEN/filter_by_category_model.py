import json
from add_cached import cached_model_call

def filter_by_category_model(data, user_category):

    def classify(category):
        text = ""
        for i, item in enumerate(data):
            text += f"{i}. {item.get('Blog_Title','')}\n"

        prompt = f"""
You are a news classifier.

Task:
Select indices of blogs related to category: "{category}"

Categories:
- finance → stock, IPO, banking, market, dividend, ex-date, record date, corporate action, bonus, split, demerger
- tech → AI, startups, software, gadgets
- health → medical, fitness, pharma
- politics → government, policy, elections
- sports → cricket, football, matches
- lifestyle → travel, fashion, food
- general → everything else

Rules:
- Understand meaning (not keyword match only)
- Ignore unrelated content

Return ONLY JSON:
{{"indices": [0,2,5]}}

Blog Titles:
{text}
"""

        result = cached_model_call(prompt)

        try:
            parsed = json.loads(result)
            indices = parsed.get("indices", [])

            valid_indices = [
                i for i in indices
                if isinstance(i, int) and 0 <= i < len(data)
            ]

            return [data[i] for i in valid_indices]

        except:
            print("Parsing failed:", result)
            return []

    # 🔹 Step 1: Try user category
    category_data = classify(user_category)

    if category_data:
        print(f"[INFO] Found {len(category_data)} blogs for category: {user_category}")
        return category_data,"user"

    # 🔹 Step 2: Fallback to finance
    print(f"[WARNING] No '{user_category}' news → fallback to FINANCE")

    finance_data = classify("finance")

    if finance_data:
        print(f"[INFO] Found {len(finance_data)} finance blogs")
        return finance_data,"finance"

    # 🔹 Step 3: Final fallback
    print("[WARNING] No finance news → returning original data")
    return data,"fallback"