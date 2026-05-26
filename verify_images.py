from PIL import Image
import json

data = json.load(open('output/output.json'))
item = data[0]

for label, path in [
    ('outer', item['blog_image']['jpg']),
    ('inner', item['blog_image_inner']['jpg']),
    ('insta', item['instagram_image']['jpg']),
]:
    img = Image.open(path)
    print(f'{label:10} -> {img.size}')