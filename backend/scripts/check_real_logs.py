"""Query Log Analytics workspace directly via REST API to check for real logs."""
import subprocess, json, urllib.request, urllib.error

WORKSPACE_ID = "f648df66-7792-4cec-942b-7b933109105c"
SUB = "ffe9a8d4-3d21-44e9-8288-f86ddae2d807"

QUERIES = {
    "APIM_GatewayLogs":  "ApiManagementGatewayLogs | where TimeGenerated > ago(3h) | summarize count() by tostring(ResponseCode) | order by count_ desc",
    "AppGW_AccessLogs":  "AzureDiagnostics | where TimeGenerated > ago(3h) and Category == 'ApplicationGatewayAccessLog' | summarize count() by httpStatus_d",
    "AppGW_AllDiag":     "AzureDiagnostics | where TimeGenerated > ago(3h) | summarize count() by Category, ResourceType | order by count_ desc | take 10",
    "AllTables_Recent":  "search * | where TimeGenerated > ago(3h) | summarize count() by Type | order by count_ desc | take 15",
}

def get_token():
    r = subprocess.run(
        ["C:\\Program Files\\Microsoft SDKs\\Azure\\CLI2\\wbin\\az.cmd",
         "account", "get-access-token",
         "--resource", "https://api.loganalytics.io/",
         "--query", "accessToken", "-o", "tsv"],
        capture_output=True, text=True)
    return r.stdout.strip()

def run_query(token, query):
    url = f"https://api.loganalytics.io/v1/workspaces/{WORKSPACE_ID}/query"
    body = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            tables = data.get("tables", [])
            if not tables: return []
            cols = [c["name"] for c in tables[0]["columns"]]
            return [dict(zip(cols, row)) for row in tables[0]["rows"]]
    except urllib.error.HTTPError as e:
        return [{"error": e.read().decode()[:200]}]
    except Exception as e:
        return [{"error": str(e)}]

if __name__ == "__main__":
    print("Getting Log Analytics token...")
    token = get_token()
    print(f"Token: {len(token)} chars\n")

    for name, query in QUERIES.items():
        print(f"=== {name} ===")
        rows = run_query(token, query)
        if not rows:
            print("  (no results)")
        for row in rows:
            print(f"  {row}")
        print()
