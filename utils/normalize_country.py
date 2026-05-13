import json
from add_cached import cached_model_call

def filter_by_country_model(data, user_country):
    # Step 1: Prepare titles
    text = ""
    for i, item in enumerate(data):
        title = item.get("Blog_Title", "")
        text += f"{i}. {title}\n"

    # Step 2: Prompt
    prompt = f"""You are a geographic blog filter. Your only job is to return a JSON object.

COUNTRY: "{user_country}"

TASK: From the numbered blog titles below, return the 0-based indices of titles where "{user_country}" is the PRIMARY subject — meaning the title is specifically and directly about that country, its government, cities, institutions, leaders, or economy, finance.

INCLUDE if the title contains:
- The country name itself
- Widely known institutions (e.g., central banks, stock exchanges, government bodies)
- Capital or major cities
- Heads of state or prominent national figures

EXCLUDE if:
- The title is global/generic with no country-specific focus
- "{user_country}" is mentioned secondarily (e.g., "Global summit including {user_country}")
- The title covers multiple countries with no primary focus on "{user_country}"
- You are unsure — omit rather than guess

Blog Titles (0-indexed):
{text}

Respond with ONLY this JSON. No text before or after:
{{"indices": [int, ...]}}

If no titles match, respond with:
{{"indices": []}}

"""



    # Step 3: Call model
    result = cached_model_call(prompt)

    # Step 4: Parse safely
    try:
        parsed = json.loads(result)
        indices = parsed.get("indices", [])

        # Safety check
        valid_indices = [
            i for i in indices
            if isinstance(i, int) and 0 <= i < len(data)
        ]

        return [data[i] for i in valid_indices]

    except Exception as e:
        print("Parsing failed")
        print("RAW:", result)
        return []