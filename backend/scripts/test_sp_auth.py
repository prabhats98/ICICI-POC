"""Test Service Principal authentication against Log Analytics."""
import urllib.request, urllib.parse, json

TENANT = "19c4bcf5-78db-4c77-b6cc-2e801774552f"
CLIENT_ID = "b3ae6c17-287d-4ba6-9571-ef2c78aa2a90"
CLIENT_SECRET = "mCu8Q~6Qhrg-t_Gswpu.j0Zqss_FxU_gXGYBTc27"
WORKSPACE_ID = "f648df66-7792-4cec-942b-7b933109105c"

token_url = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token"
body = urllib.parse.urlencode({
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "https://api.loganalytics.io/.default"
}).encode()

req = urllib.request.Request(token_url, data=body, method="POST")
req.add_header("Content-Type", "application/x-www-form-urlencoded")

try:
    r = urllib.request.urlopen(req, timeout=15)
    d = json.loads(r.read())
    token = d.get("access_token", "")
    print(f"SP Token OK: {len(token)} chars")

    url = f"https://api.loganalytics.io/v1/workspaces/{WORKSPACE_ID}/query"
    body2 = json.dumps({"query": "AzureDiagnostics | take 2"}).encode()
    req2 = urllib.request.Request(url, data=body2, method="POST")
    req2.add_header("Authorization", f"Bearer {token}")
    req2.add_header("Content-Type", "application/json")
    r2 = urllib.request.urlopen(req2, timeout=15)
    d2 = json.loads(r2.read())
    rows = d2.get("tables", [{}])[0].get("rows", [])
    print(f"Query OK: {len(rows)} rows")
except urllib.request.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode()[:300]}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
