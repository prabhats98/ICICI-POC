import sqlite3, os, urllib.request, json

db = r"c:\Users\Prabhat Singh\Downloads\ICICI\banking-cloud-log-analyser\backend\banking_log_analyser.db"
if not os.path.exists(db):
    print("DB NOT FOUND at", db)
else:
    con = sqlite3.connect(db)
    cur = con.cursor()
    tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print("Tables:", [t[0] for t in tables])
    for t in [r[0] for r in tables]:
        count = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {count} rows")
        if count > 0 and t in ("incidents", "cloud_logs", "agent_runs"):
            row = cur.execute(f"SELECT * FROM {t} LIMIT 1").fetchone()
            cols = [d[0] for d in cur.description]
            print(f"    Sample: {dict(zip(cols[:6], row[:6]))}")
    con.close()

print("\n--- API checks ---")
for url in [
    "http://localhost:8000/api/dashboard",
    "http://localhost:8000/api/incidents/?page_size=5",
    "http://localhost:8000/api/analytics/incident-trend",
]:
    try:
        r = urllib.request.urlopen(url, timeout=5)
        data = json.loads(r.read())
        print(f"GET {url.split('8000')[1]}: {str(data)[:150]}")
    except Exception as e:
        print(f"GET {url.split('8000')[1]}: ERROR {e}")
