import json
from add_cached import cached_model_call

def generate_blog(item):
  prompt = f"""
You are a fintech content writer.

Write a blog based on the news below.

NEWS:
Title: {item['Blog_Title']}
Content: {item['Blog_Content']}

Return ONLY valid JSON in this format:

{{
  "Meta_Title": "SEO friendly title under 60 characters",
  "Meta_Description": "Short description under 160 characters",
  "TLDR": [
    "Key insight from news",
    "Sector or stock impact",
    "Cause or trigger",
    "What to watch next"
  ],
  "Blog_Title": "Catchy blog title",
  "Blog_Content": "HTML blog using H1, H2, H3, p tags (600-900 words)",
  "FAQ_Schema": {{
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
      {{
        "@type": "Question",
        "name": "User question",
        "acceptedAnswer": {{
          "@type": "Answer",
          "text": "Clear short answer"
        }}
      }}
    ]
  }},
  "Conclusion": "Short summary",
  "CTA": "https://trade.swastika.co.in/"
}}

Rules:
- Keep content simple, clear, and original
- Do not copy text from input
- No markdown, only JSON output
- No extra text outside JSON
- TLDR must have exactly 4 points (specific to this news)
- Generate exactly 4 FAQs

SWASTIKA RULE:
- Include Swastika Investmart in ONLY ONE paragraph inside Blog_Content
- That paragraph must be 2–5 sentences maximum
- It must be naturally blended within the blog (not a separate section)
- Do NOT make it sound like promotion or advertisement
- Do NOT use call-to-action language (no “start trading”, “sign up”, etc.)
- Keep it informational, subtle, and relevant to the topic

QUALITY:
- Blog length: 600–900 words
- Use H1, H2, H3, and paragraph tags properly
- Write in a beginner-friendly, conversational tone
"""

  result = cached_model_call(prompt)
  data = json.loads(result)
  return data
  
  
 
#     prompt = f"""
# You are a fintech-focused SEO blog expert.

# Generate a plagiarism-free blog post using the following keyword:
# Return the output STRICTLY in the following JSON format (no extra text, no explanation, no \\n):

# {{
#   "Meta_Title": "",
#   "Meta_Description": "",
#   "TLDR": ["", "", ""],
#   "Blog_Title": "",
#   "Blog_Content": "",
#    "FAQ_Schema": {{
#     "@context": "https://schema.org",
#     "@type": "FAQPage",
#     "mainEntity": [
#       {{
#         "@type": "Question",
#         "name": "",
#         "acceptedAnswer": {{
#           "@type": "Answer",
#           "text": ""
#         }}
#       }}
#     ]
#   }},
#   "Conclusion": "",
#   "CTA": ""
# }}
# Rules for FAQ:
# - Generate 3–5 FAQs
# - Use JSON-LD format ONLY (schema.org)
# - No plain "FAQs" list
# - Questions must be user-focused
# - Answers must be clear and helpful
# Primary Keyword: {item['Blog_Title']}

# Your blog must include:
# - Output must be a valid JSON object
# - Do NOT use \\n anywhere
# - Do NOT return text outside JSON
# - A compelling Meta Title (≤ 60 characters) optimized for CTR
# - A persuasive Meta Description (≤ 160 characters) using the keyword
# - A TL;DR with 3–5 key bullet takeaways
# - A catchy Blog Title optimized for search intent
# - A full-length blog (~800–1200 words) with clear structure using <H1>, <H2>, <H3> tags
# - Use related financial and investing keywords naturally
# - Highlight Swastika Investmart positively (trust, research, compliance, etc.)
# Tone:
# - Professional
# - Beginner-friendly
# - Human-like (NOT robotic)

# Content must include:
# 1. Meta Title  
# 2. Meta Description  
# 3. TL;DR  
# 4. Blog Title  
# 5. Full Blog Body (800–1200 words with <H1>, <H2>, <H3>)  
# 6. FAQs (3–5 questions)  
# 7. Conclusion  

# Rules:
# - 100% original content
# - No plagiarism
# - No copying from input
# - Avoid keyword stuffing
# - Do NOT mention brokerage charges
# - Keep readability high and natural
# - Avoid using "--"

# Add CTA at the end:
# https://trade.swastika.co.in/?UTMsrc={item['Blog_Title'].replace(" ", "")}

# News Context:
# Title: {item['Blog_Title']}
# Content: {item['Blog_Content']}
# """
    


    # result = cached_model_call(prompt)
    #   # Convert string → JSON
      
    # data = json.loads(result)
    
    # return data



























































































































































































































# def generate_blog(item):
#     prompt = f"""
#   You are a finance blogger.
  

# STRICT RULES:
# - Do NOT copy phrases or sentences
# - Completely rewrite in your own words
# - Avoid plagiarism completely
# - Add explanation (what it means for people/investors)
# - Keep it simple and engaging
# - Make it feel like a blog, not raw news

# News:
# Title: {item['Blog_Title']}
# Content: {item['Blog_Content']}
#     """

#     response = client.chat.completions.create(
#         model=MODEL,
#         messages=[{"role": "user", "content": prompt}]
#     )

#     return response.choices[0].message.content