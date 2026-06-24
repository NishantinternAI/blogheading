# test_connection.py
from google.ads.googleads.client import GoogleAdsClient

try:
    client = GoogleAdsClient.load_from_storage(version="v24")
    print("CLIENT LOADED: OK")

    # List accessible accounts
    customer_service = client.get_service("CustomerService")
    accessible = customer_service.list_accessible_customers()
    print("ACCESSIBLE ACCOUNTS:")
    for resource_name in accessible.resource_names:
        print(f"  {resource_name}")

except Exception as e:
    print("FAILED:", e)