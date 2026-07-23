import json, os, unicodedata, re, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root, for content_engine
from content_engine.image_module.template_selector import select_template_pair
from content_engine.image_module.compositor import compose_image
from content_engine.image_module.text_extractor import extract_image_text

def clean(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    text = re.sub(r'[\\/*?:"<>|]', '', text)
    text = text.replace(' ', '_')
    text = re.sub(r'_+', '_', text)
    return text[:60]

with open('output/output.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total blogs: {len(data)}")

for i, item in enumerate(data):
    title      = item.get('Blog_Title', '')
    image_text = item.get('image_text') or extract_image_text(
        title, item.get('Blog_Content', ''), 'FINANCE'
    )
    pair = select_template_pair('finance', title)
    safe = clean(title)

    print(f"[{i+1}/{len(data)}] {title[:50]}")

    item['blog_image'] = compose_image(
        pair['outer'], image_text,
        f'output_images/jpg_images/blog_{safe}.jpg',
        f'output_images/webp_images/blog_{safe}.webp',
        'blog'
    )

    item['blog_image_inner'] = compose_image(
        pair['inner'], {},
        f'output_images/jpg_images/blog_inner_{safe}.jpg',
        f'output_images/webp_images/blog_inner_{safe}.webp',
        'blog_inner'
    )

    item['instagram_image'] = compose_image(
        pair['outer'], image_text,
        f'output_images/jpg_images/insta_{safe}.jpg',
        f'output_images/webp_images/insta_{safe}.webp',
        'instagram'
    )

with open('output/output.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("Done! All images regenerated.")