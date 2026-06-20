"""
Configure Azure diagnostic settings for App Gateway and APIM
to send logs to the Log Analytics workspace.
"""

import subprocess
import json
import urllib.request
import urllib.error
import sys

SUB = "ffe9a8d4-3d21-44e9-8288-f86ddae2d807"
RG = "banking-log-analyser-rg"
WORKSPACE_ID = f"/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.OperationalInsights/workspaces/banking-log-analyser"

RESOURCES = {
    "APIM": {
        "id": f"/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.ApiManagement/service/banking-log-apim",
        "logs": ["GatewayLogs"],
    },
    "AppGateway": {
        "id": f"/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.Network/applicationGateways/banking-appgw",
        "logs": ["ApplicationGatewayAccessLog", "ApplicationGatewayPerformanceLog", "ApplicationGatewayFirewallLog"],
    },
}


def get_token():
    result = subprocess.run(
        ["C:\\Program Files\\Microsoft SDKs\\Azure\\CLI2\\wbin\\az.cmd",
         "account", "get-access-token",
         "--resource", "https://management.azure.com/",
         "--query", "accessToken", "-o", "tsv"],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def create_diagnostic_setting(token, resource_id, name, log_categories, workspace_id):
    url = (
        f"https://management.azure.com{resource_id}"
        f"/providers/Microsoft.Insights/diagnosticSettings/{name}"
        f"?api-version=2021-05-01-preview"
    )

    body = {
        "properties": {
            "workspaceId": workspace_id,
            "logs": [
                {"category": cat, "enabled": True}
                for cat in log_categories
            ],
            "metrics": [{"category": "AllMetrics", "enabled": True}]
        }
    }

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="PUT")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            print(f"  OK: {result.get('name', 'created')}")
            return True
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        print(f"  HTTP {e.code} error: {body_text[:300]}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


if __name__ == "__main__":
    print("Getting Azure token...")
    token = get_token()
    print(f"Token: {len(token)} chars\n")

    for resource_name, config in RESOURCES.items():
        print(f"Configuring {resource_name} -> Log Analytics...")
        ok = create_diagnostic_setting(
            token=token,
            resource_id=config["id"],
            name="send-to-log-analytics",
            log_categories=config["logs"],
            workspace_id=WORKSPACE_ID,
        )
        if ok:
            print(f"  {resource_name} diagnostic settings: DONE")
        else:
            print(f"  {resource_name} diagnostic settings: FAILED")

    print("\nDone. Logs will flow to Log Analytics within 5-10 minutes of traffic.")
