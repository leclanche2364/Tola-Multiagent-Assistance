"""Nightly live data pull for RC + Shiftlyx. Run: python3 scripts/daily_pull.py [--date YYYY-MM-DD]

Pulls headline metrics from PostHog/GA4/GSC, prints a Discord-ready summary,
and saves a JSON snapshot under data/daily_pull/. Read-only against external
services; only local writes are the snapshot file.
"""
import sys, os, json, datetime, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from adapters import env as env_mod
from adapters import posthog_adapter, ga4_adapter, gsc_adapter

E = env_mod.load_env()

PRODUCTS = {
    "revalidation_copilot": {"ga4": "revalidation_copilot", "phog": "revalidation_copilot"},
    "shiftlyx": {"ga4": "shiftlyx", "phog": "shiftlyx"},
}

def week_range(end_date):
    end = datetime.date.fromisoformat(end_date)
    start = end - datetime.timedelta(days=6)
    return start.isoformat(), end.isoformat()

def pull(product, start, end):
    out = {"product": product, "window": [start, end], "sources": {}}
    ga4_cfg = PRODUCTS[product]["ga4"]
    try:
        rows = ga4_adapter.run_report(ga4_cfg, ["date"], ["activeUsers", "sessions"], start, end, env_dict=E)
        users = sum(int(r["activeUsers"]) for r in rows if r.get("activeUsers") and str(r["activeUsers"]).isdigit())
        sessions = sum(int(r["sessions"]) for r in rows if r.get("sessions") and str(r["sessions"]).isdigit())
        out["sources"]["ga4"] = {"activeUsers": users, "sessions": sessions, "status": "OK"}
    except Exception as e:
        out["sources"]["ga4"] = {"status": "FAIL", "error": str(e)[:120]}
    try:
        summary = posthog_adapter.get_project_summary(PRODUCTS[product]["phog"], E)
        out["sources"]["posthog"] = {"status": "OK", "id": summary.get("id"), "name": summary.get("name")}
    except Exception as e:
        out["sources"]["posthog"] = {"status": "FAIL", "error": str(e)[:120]}
    return out

def brief(reports):
    lines = ["**Daily growth pull** — window %s to %s" % (reports[0]["window"][0], reports[0]["window"][1])]
    for r in reports:
        ga4 = r["sources"].get("ga4", {})
        if ga4.get("status") == "OK":
            lines.append("• %s: %s active users, %s sessions (GA4)" % (r["product"], ga4["activeUsers"], ga4["sessions"]))
        else:
            lines.append("• %s: GA4 FAIL — %s" % (r["product"], ga4.get("error", "?")))
        ph = r["sources"].get("posthog", {})
        lines.append("  PostHog: %s" % ph.get("status", "?"))
    fails = [r["product"] for r in reports for s in r["sources"].values() if s.get("status") == "FAIL"]
    lines.append("Data quality: %s" % ("FAIL on %s" % ", ".join(fails) if fails else "PASS"))
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    args = ap.parse_args()
    start, end = week_range(args.date)
    reports = [pull(p, start, end) for p in PRODUCTS]
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "daily_pull")
    os.makedirs(out_dir, exist_ok=True)
    snap_path = os.path.join(out_dir, "%s.json" % end)
    with open(snap_path, "w") as f:
        json.dump({"pulled_at": datetime.datetime.now().isoformat(), "reports": reports}, f, indent=1)
    print(brief(reports))
    print("snapshot: %s" % snap_path)
    sys.exit(0)

if __name__ == "__main__":
    main()