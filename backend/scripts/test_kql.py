"""Test the fixed KQL queries with column_ifexists."""
import urllib.request, urllib.parse, json

TENANT = "19c4bcf5-78db-4c77-b6cc-2e801774552f"
CLIENT_ID = "b3ae6c17-287d-4ba6-9571-ef2c78aa2a90"
CLIENT_SECRET = "mCu8Q~6Qhrg-t_Gswpu.j0Zqss_FxU_gXGYBTc27"
WORKSPACE_ID = "f648df66-7792-4cec-942b-7b933109105c"
HOURS = 6

def get_token():
    url = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token"
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials", "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET, "scope": "https://api.loganalytics.io/.default"
    }).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read())["access_token"]

def run_query(token, name, query):
    url = f"https://api.loganalytics.io/v1/workspaces/{WORKSPACE_ID}/query"
    body = json.dumps({"query": query}).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        r = urllib.request.urlopen(req, timeout=20)
        d = json.loads(r.read())
        rows = d.get("tables", [{}])[0].get("rows", [])
        print(f"  [{name}] OK: {len(rows)} rows")
        if rows:
            cols = [c["name"] for c in d["tables"][0]["columns"]]
            print(f"    Sample: {dict(zip(cols, rows[0]))}")
    except urllib.request.HTTPError as e:
        print(f"  [{name}] HTTP {e.code}: {e.read().decode()[:300]}")

QUERIES = {
    "AppGW_fixed": f"""AzureDiagnostics
| where TimeGenerated > ago({HOURS}h)
| where ResourceProvider == "MICROSOFT.NETWORK"
| where Category in ("ApplicationGatewayAccessLog", "ApplicationGatewayPerformanceLog", "ApplicationGatewayFirewallLog")
| extend httpStat = column_ifexists("httpStatus_d", 0.0)
| extend srvStat  = column_ifexists("serverStatus_d", 0.0)
| extend StatusCode = toint(iff(httpStat > 0, httpStat, srvStat))
| extend Level = iff(StatusCode >= 500, "Error", iff(StatusCode >= 400, "Warning", "Information"))
| extend host_s       = column_ifexists("host_s", "")
| extend requestUri_s = column_ifexists("requestUri_s", "")
| extend clientIP_s   = column_ifexists("clientIP_s", "")
| extend timeTaken_d  = column_ifexists("timeTaken_d", 0.0)
| extend instanceId_s = column_ifexists("instanceId_s", "")
| project TimeGenerated, Level, Category, OperationName, ResourceId,
          httpStatus_d = httpStat, serverStatus_d = srvStat, timeTaken_d,
          host_s, requestUri_s, clientIP_s, instanceId_s,
          ResultDescription = tostring(StatusCode)
| order by TimeGenerated desc
| limit 5""",

    "APIM_fixed": f"""ApiManagementGatewayLogs
| where TimeGenerated > ago({HOURS}h)
| extend Level = iff(ResponseCode >= 500, "Error", iff(ResponseCode >= 400, "Warning", "Information"))
| order by TimeGenerated desc
| limit 5""",
}

token = get_token()
print(f"Token: {len(token)} chars\n")
for name, q in QUERIES.items():
    run_query(token, name, q)
