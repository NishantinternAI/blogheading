from functools import lru_cache
from config import client, MODEL

# ✅ Trackers
total_cost = 0.0
api_call_count = 0  # ✅ Add this

def reset_cost_tracker():
    global total_cost, api_call_count
    total_cost = 0.0
    api_call_count = 0  # ✅ Reset counter

def get_total_cost():
    return total_cost

def get_api_call_count():
    return api_call_count  # ✅ Return count

@lru_cache(maxsize=200)
def cached_model_call(prompt):
    global total_cost, api_call_count
    api_call_count += 1  # ✅ Count every call
    print(f"Calling API... (Call #{api_call_count})")  # ✅ Shows call number

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You must return a valid JSON response only."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )

    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    cost = (input_tokens / 1_000_000) * 3 + (output_tokens / 1_000_000) * 15
    total_cost += cost

    print(f"   Input Tokens  : {input_tokens}")
    print(f"   Output Tokens : {output_tokens}")
    print(f"   💰 Call Cost   : ${cost:.6f}")

    return response.choices[0].message.content
# from functools import lru_cache
# from config import client, MODEL

# @lru_cache(maxsize=200)
# def cached_model_call(prompt):
#     print(" Calling API...")

#     response = client.chat.completions.create(
#         model=MODEL,
#         messages=[
#             {"role": "system", "content": "You must return a valid JSON response only."},
            
#             {"role": "user", "content": prompt}],
#         response_format={"type": "json_object"}  # IMPORTANT
#     )

#     return response.choices[0].message.content