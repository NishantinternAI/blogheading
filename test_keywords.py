# test_keywords.py
from google.ads.googleads.client import GoogleAdsClient

CUSTOMER_ID = "2948017527"   # your customer ID without dashes

client  = GoogleAdsClient.load_from_storage(version="v24")
service = client.get_service("KeywordPlanIdeaService")

request = client.get_type("GenerateKeywordIdeasRequest")
request.customer_id   = CUSTOMER_ID
request.language      = client.get_service("GoogleAdsService").language_constant_path("1000")
request.geo_target_constants = [
    client.get_service("GeoTargetConstantService").geo_target_constant_path("2356")
]
request.include_adult_keywords = False
request.keyword_plan_network   = (
    client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH_AND_PARTNERS
)

# Test with IFCI — a topic your pipeline already processed
request.keyword_seed.keywords.extend([
    "IFCI share price",
    "IFCI stock",
    "NSE corporate actions"
])

ideas = service.generate_keyword_ideas(request=request)

print(f"{'KEYWORD':<45} {'MONTHLY SEARCHES':>18} {'COMPETITION':>14}")
print("-" * 80)
for idea in ideas:
    print(
        f"{idea.text:<45}"
        f"{idea.keyword_idea_metrics.avg_monthly_searches:>18,}"
        f"{idea.keyword_idea_metrics.competition.name:>14}"
    )