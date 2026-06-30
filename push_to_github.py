"""
Push CloudGuard_Validation_Checklist.xlsx to GitHub via the GitHub REST API.
Uses the Contents API to create/update a file in the repository.
"""

import base64
import json
import urllib.request
import urllib.error
import ssl
import os
import getpass

# SSL context for Windows
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

REPO = "prabhats98/ICICI-POC"
FILE_PATH = "CloudGuard_Validation_Checklist.xlsx"
LOCAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), FILE_PATH)
BRANCH = "dev_branch"
COMMIT_MSG = "Add CloudGuard Stakeholder Validation Checklist (48 items across 5 domains)"

API_URL = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"


def get_existing_sha(token):
    """Check if the file already exists and get its SHA (needed for updates)."""
    req = urllib.request.Request(f"{API_URL}?ref={BRANCH}", method="GET")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    try:
        resp = urllib.request.urlopen(req, timeout=30, context=ssl_ctx)
        data = json.loads(resp.read().decode())
        return data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def push_file(token):
    # Read the local file
    with open(LOCAL_FILE, "rb") as f:
        content = base64.b64encode(f.read()).decode("ascii")

    print(f"File size: {os.path.getsize(LOCAL_FILE):,} bytes")
    print(f"Target: {REPO}/{FILE_PATH} (branch: {BRANCH})")

    # Check if file exists (need SHA for update)
    sha = get_existing_sha(token)
    if sha:
        print(f"File exists (SHA: {sha[:8]}...), will update.")
    else:
        print("File does not exist, will create.")

    # Build the payload
    payload = {
        "message": COMMIT_MSG,
        "content": content,
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha

    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(API_URL, data=body, method="PUT")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("Content-Type", "application/json")

    try:
        resp = urllib.request.urlopen(req, timeout=60, context=ssl_ctx)
        result = json.loads(resp.read().decode())
        commit_sha = result.get("commit", {}).get("sha", "unknown")
        html_url = result.get("content", {}).get("html_url", "")
        print(f"\n[OK] Successfully pushed to GitHub!")
        print(f"  Commit: {commit_sha[:12]}")
        print(f"  URL: {html_url}")
        return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"\n[ERROR] GitHub API returned {e.code}: {e.reason}")
        print(f"  Details: {error_body[:300]}")
        return False


if __name__ == "__main__":
    # Try environment variable first, then prompt
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("GitHub Personal Access Token required (needs 'repo' scope).")
        print("Generate one at: https://github.com/settings/tokens")
        token = getpass.getpass("Enter GitHub Token: ")

    if not token.strip():
        print("[ERROR] No token provided. Exiting.")
        exit(1)

    push_file(token.strip())
