import json
from config import client, MODEL
from add_cached import cached_model_call

# 
def create_batch_prompt(data):
    text = ""
    for i, item in enumerate(data):
        text += f"{i}. {item['Blog_Title']}\n"
    return text


def filter_finance_batch(data):
    text = create_batch_prompt(data)

    prompt = f"""
    Classify each news as FINANCE or NOT.

STRICT RULES:

Mark FINANCE ONLY if news is about:
- stock market, shares, trading
- banking, RBI, interest rates
- company earnings, results
- IPO, investments, mutual funds

Mark NOT if news is about:
- war, geopolitics, global conflicts
- general economy without finance angle
- inflation without market impact
- energy prices or global news.
STRICT RULES:
- Return ONLY valid JSON
- Do NOT add any explanation
- Do NOT add text like "Here are results"
- Output must be a JSON object
Return Format-
Example:
{{"0": "FINANCE", "1": "NOT", "2": "FINANCE"}}

    {text}

   
    """

    result = cached_model_call(prompt)
      # Convert string → JSON
    try:
        data = json.loads(result)

    
    except Exception as e:
        print(" JSON parsing failed")
        print("RAW RESPONSE:\n",result)
        raise e
    
    return data

