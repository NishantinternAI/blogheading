import random
import re
import unicodedata
import sys
from filter_blogs_country import  filter_by_country
from RSS.zerodha import fetch_zerodha
from RSS.cnbc import fetch_cnbc
from RSS.paisa import fetch_5paisa
from RSS.livemint import fetch_livemint
from RSS.fetch_nse_corporate import fetch_nse_corporate

from content_engine.image_module.text_extractor import extract_image_text
from content_engine.image_module.tempalte_selector import select_template
from content_engine.image_module.compositor import compose_image
from content_engine.image_module.validator import validate_template



from dynamic_input_country import get_args

from AI_GEN.filter_by_category_model import filter_by_category_model
from AI_GEN.notify_generator import generate_notification
from AI_GEN.generate_instagram_caption import generate_instagram_caption
from AI_GEN.get_system_timestamp import get_run_timestamp


from Filter_news.finance_filter import filter_finance_batch
from utils.parser import parse_finance_response
from utils.normalize_country import filter_by_country_model
from AI_GEN.blog_generator import generate_blog
from storage.save_output import save_output




def clean_filename(text):
    # Normalize unicode (₹, ’ → removed/converted)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()

    # Remove invalid Windows characters
    text = re.sub(r'[\\/*?:"<>|]', '', text)

    # Replace spaces with underscore
    text = text.replace(" ", "_")

    # Remove multiple underscores
    text = re.sub(r'_+', '_', text)

    return text[:60]

# all_data = []

# all_data.extend(fetch_zerodha())
# all_data.extend(fetch_cnbc())
# all_data.extend(fetch_5paisa())
# all_data.extend(fetch_livemint())
# all_data.extend(fetch_nse_corporate())

TOP_N = 20

all_data = []
all_data.extend(fetch_zerodha()[:TOP_N])
all_data.extend(fetch_cnbc()[:TOP_N])
all_data.extend(fetch_5paisa()[:TOP_N])
all_data.extend(fetch_livemint()[:TOP_N])
all_data.extend(fetch_nse_corporate()[:TOP_N])

print(f"Total collected: {len(all_data)}")


# print(len(all_data))
args = get_args()
selected_country = args.country
print("User country:", selected_country)

filtered_data = filter_by_country_model(all_data, selected_country)

print("After country filter:", len(filtered_data)) 
if not filtered_data:
    print("[WARNING] No country match → using ALL data")
    filtered_data = all_data

category = args.category
print("User category:", category)
category_filtered_data,source = filter_by_category_model(filtered_data, category)

print("After category filter:", len(category_filtered_data))

working_data = category_filtered_data
print("Final data after category :", len(working_data))

# Step 2: Filter using AI (Batch)
# response_text = filter_finance_batch(all_data)

# finance_news = parse_finance_response(response_text, all_data)


# response_text = filter_finance_batch(filtered_data)
# finance_news = parse_finance_response(response_text, filtered_data)

# print("Finance news count:", len(finance_news))


# ── Step 4: Save each finance news item ──────────────────────────────────────



# Step 3: Decision logic
if working_data:
    if source=='user':
        print(f"{category.upper()} news found → generating blogs")
        final_category = category
    elif source=="finance":
        print("Finance fallback used → generating blogs")
        final_category = "finance"
    else:
        print("General data used → generating blogs")
        final_category = "general"
    for item in working_data:
        item["blog"] = generate_blog(item)
        item["notify"] = generate_notification(item)
        item["instagram_notify"] = generate_instagram_caption(item)

        item_category = category if category else "GENERAL"

        item["image_text"] = extract_image_text(
        item["Blog_Title"],
        item["Blog_Content"],
        final_category.upper()
        )
        item["template_path"] = select_template(
        final_category,
        item["Blog_Title"]
        )
        print("Template selected:", item["template_path"])

        
        validate_template(item["template_path"])

        # safe_title = item["Blog_Title"][:40].replace(" ", "_").replace("/", "")
        safe_title = clean_filename(item["Blog_Title"])
        # --- BLOG IMAGE ---
        blog_output_path = f"output_images/blog_{safe_title}.jpg"
        item["blog_image"] = compose_image(
        item["template_path"],
        item["image_text"],
        blog_output_path,
        image_type="blog"
        )
        # --- INSTAGRAM IMAGE ---
        insta_output_path = f"output_images/insta_{safe_title}.jpg"
        item["instagram_image"] = compose_image(
        item["template_path"],
        item["image_text"],
        insta_output_path,
        image_type="instagram"
        )
        # item["final_image"] = compose_image(
        # item["template_path"],
        # item["image_text"],
        # output_path
        # )
        item["Run_Timestamp"] = get_run_timestamp()

        save_output(item)

    # select the random finance news 
    # selected_data = random.sample(finance_news, min(5, len(finance_news)))
    # final_item = random.choice(selected_data)
    

    # final_item["blog"] = generate_blog(final_item)
    # final_item["notify"] = generate_notification(final_item)
    # final_item["instagram_notify"]=generate_instagram_caption(final_item)
    # final_item["Run_Timestamp"]=get_run_timestamp()
    # selected_data = [final_item]


else:
    print("No finance news → fallback to Zerodha")

    zerodha_data = fetch_zerodha()
    final_item = zerodha_data[0]
    # Step 2: generate blog
    final_item["blog"] = generate_blog(final_item)
    final_item["notify"] = generate_notification(final_item)
    final_item["instagram_notify"]=generate_instagram_caption(final_item)
    final_item["Run_Timestamp"]=get_run_timestamp()
    


    selected_data = [final_item]

    


# Step 4: Save output
    save_output(final_item)
print(" Process completed")








