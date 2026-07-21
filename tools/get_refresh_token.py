# get_refresh_token.py
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json",
    scopes=["https://www.googleapis.com/auth/adwords"]
)

creds = flow.run_local_server(port=9090)

print("=" * 50)
print("REFRESH TOKEN :", creds.refresh_token)
print("ACCESS TOKEN  :", creds.token)
print("=" * 50)
print("\nCopy the REFRESH TOKEN into your google-ads.yaml")