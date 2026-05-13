from functools import lru_cache
from config import client, MODEL

@lru_cache(maxsize=200)
def cached_model_call(prompt):
    print(" Calling API...")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You must return a valid JSON response only."},
            
            {"role": "user", "content": prompt}],
        response_format={"type": "json_object"}  # IMPORTANT
    )

    return response.choices[0].message.content