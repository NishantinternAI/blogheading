def parse_finance_response(response_text, data):
    finance_news = []

    import json

    # Step 1: Convert string → dict
    if isinstance(response_text, str):
        response_text = json.loads(response_text)

    # Step 2: Loop safely
    for index, label in response_text.items():
        try:
            index = int(str(index).strip())
        except:
            print("Skipping invalid index:", index)
            continue

        

        # FIX: handle list case
        if isinstance(label, list):
            label = " ".join(map(str, label))

        # Extra safety
        if isinstance(label, str) and "FINANCE" in label.upper():
            if index < len(data):
                finance_news.append(data[int(index)])

            

    return finance_news



















































# def parse_finance_response(response_text, data):
#     finance_news = []

#     if isinstance(response_text, str):
#         import json
#         response_text = json.loads(response_text)


#     for index, label in response_text.items():
#         if "FINANCE" in label.upper():
#             finance_news.append(data[int(index)])
        
#     return finance_news