"""Builds the published-assets manifest by scanning the Revalidation-Website repo.

Run: python3 scripts/build_assets_manifest.py
Auto-discovers live pages and blog posts, extracts titles/target keywords,
and writes assets_manifest.json. Cheap, deterministic, no model involved.
Schedule it as a daily command cron so the manifest never goes stale.
"""
import os, re, json, datetime, glob

SITE = os.path.expanduser("~/.openclaw/workspace-growth/Revalidation-Website")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "assets_manifest.json")

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
DESC_RE = re.compile(r'<meta name="description" content="(.*?)"', re.S | re.I)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S | re.I)

def scan_html(path):
    try:
        html = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return None
    t = TITLE_RE.search(html)
    d = DESC_RE.search(html)
    h1 = H1_RE.search(html)
    return {
        "file": os.path.relpath(path, SITE),
        "title": re.sub(r"<[^>]+>", "", t.group(1)).strip() if t else "",
        "description": re.sub(r"<[^>]+>", "", d.group(1)).strip()[:160] if d else "",
        "h1": re.sub(r"<[^>]+>", "", h1.group(1)).strip() if h1 else "",
    }

def main():
    entries = []
    for pattern in ("*.html", "blog/*.html"):
        for path in sorted(glob.glob(os.path.join(SITE, pattern))):
            name = os.path.basename(path)
            if name in ("404.html",) or ".bak" in name:
                continue
            info = scan_html(path)
            if info and info["title"]:
                entries.append(info)
    manifest = {
        "generated_at": datetime.datetime.now().isoformat(),
        "source_repo": SITE,
        "count": len(entries),
        "assets": entries,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(manifest, f, indent=1)
    print("manifest: %s (%d assets)" % (OUT, len(entries)))

if __name__ == "__main__":
    main()