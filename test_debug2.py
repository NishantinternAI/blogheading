import json

with open("output/output.json", "r", encoding="utf-8") as f:
    blogs = json.load(f)

last_100 = blogs[-100:]

for blog in last_100:
    print(blog,end="\n")