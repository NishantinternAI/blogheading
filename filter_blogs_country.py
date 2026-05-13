def filter_by_country(data, country="India"):
    country = country.lower()

    def match(item, keyword):
        text = (item.get("Title", "") + " " + item.get("Blog_Content", "")).lower()
        return keyword in text

    filtered = []

    # Step 1: filter + tag
    for item in data:
        if match(item, country):
            item["Detected_Country"] = country.upper()
            filtered.append(item)

    # Step 2: if found → return
    if filtered:
        print(f"[INFO] Found {len(filtered)} blogs for {country}")
        return filtered

    # Step 3: SPECIAL CASE (India → return all data)
    if country == "india":
        print("[WARNING] No India blogs found → returning ALL data")

        for item in data:
            item["Detected_Country"] = "ALL"

        return data

    # Step 4: for other countries → fallback to India (optional)
    print(f"[WARNING] No blogs found for '{country}', fallback to India")

    india_filtered = []

    for item in data:
        if match(item, "india"):
            item["Detected_Country"] = "INDIA"
            india_filtered.append(item)

    return india_filtered if india_filtered else data


























































































































































































# def filter_by_country(data, country="India"):
#     country = country.lower()

#     def match(item, keyword):
#         text = (item.get("Title", "") + " " + item.get("Blog_Content", "")).lower()
#         return keyword in text

#     filtered = []

#     # Step 1: filter + tag country
#     for item in data:
#         if match(item, country):
#             item["Detected_Country"] = country.upper()
#             filtered.append(item)

#     # Step 2: if found → return
#     if filtered:
#         print(f"[INFO] Found {len(filtered)} blogs for {country}")
#         return filtered

#     # Step 3: fallback to India
#     print(f"[WARNING] No blogs found for '{country}', fallback to India")

#     india_filtered = []

#     for item in data:
#         if match(item, "india"):
#             item["Detected_Country"] = "INDIA"
#             india_filtered.append(item)

#     # Step 4: final fallback
#     if india_filtered:
#         return india_filtered

#     print("[WARNING] No India blogs found → returning all data")

#     for item in data:
#         item["Detected_Country"] = "UNKNOWN"

#     return data

























































































































# def filter_by_country(data, country="India"):
#     country = country.lower()

#     def match(item, keyword):
#         text = (item.get("Title", "") + " " + item.get("Blog_Content", "")).lower()
#         return keyword in text

#     # Step 1: filter by selected country
#     filtered = [item for item in data if match(item, country)]

#     # Step 2: if found → return
#     if filtered:
#         return filtered

#     # Step 3: fallback to India
#     print(f"No blogs found for '{country}', showing India blogs")

#     india_filtered = [item for item in data if match(item, "india")]

#     return india_filtered if india_filtered else data