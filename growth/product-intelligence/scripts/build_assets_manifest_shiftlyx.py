"""Builds the Shiftlyx published-assets manifest (Next.js site).

Run: python3 scripts/build_assets_manifest_shiftlyx.py
Reads public/sitemap.xml for the live route list and page.tsx metadata for
titles/descriptions. Writes data/assets_manifest_shiftlyx.json.
Deterministic, no model involved. Schedule nightly alongside the RC manifest.
"""
import os, re, json, datetime, glob

SITE = os.path.expanduser("~/.openclaw/workspace-shiftlyx/shiftlyx-website")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "assets_manifest_shiftlyx.json")

entries = []

def route_of(url):
    path = re.sub(r"https?://[^/]+", "", url).strip("/")
    return "/" + path if path else "/"

# 1) sitemap URLs (live routes)
try:
    sm = open(os.path.join(SITE, "public", "sitemap.xml")).read()
    for url in re.findall(r"<loc>(.*?)</loc>", sm):
        entries.append({"file": "route:" + route_of(url), "url": url, "title": "", "description": ""})
except OSError:
    pass

# 2) page.tsx metadata objects
meta_re = re.compile(r"metadata\s*[:=]\s*\{(.*?)\n\}", re.S)
t_re = re.compile(r"""title\s*[:=]\s*["'`]?([^\n"'`,}]+)""")
d_re = re.compile(r"""description\s*[:=]\s*["'`]?([^\n"'`,}]+)""")

for p in sorted(glob.glob(os.path.join(SITE, "src/app/**/page.tsx"), recursive=True)):
    src = open(p, encoding="utf-8", errors="ignore").read()
    m = meta_re.search(src)
    blob = m.group(1) if m else src[:4000]
    t, d = t_re.search(blob), d_re.search(blob)
    route = os.path.relpath(os.path.dirname(p), os.path.join(SITE, "src", "app"))
    route = "/" if route == "." or route.startswith("(") else "/" + route
    key = "route:" + route
    for e in entries:
        if e["file"] == key:
            e["title"] = t.group(1).strip() if t else e["title"]
            e["description"] = (d.group(1).strip()[:160]) if d else e["description"]
            break
    else:
        entries.append({"file": key, "title": t.group(1).strip() if t else "",
                        "description": (d.group(1).strip()[:160]) if d else ""})

manifest = {
    "generated_at": datetime.datetime.now().isoformat(),
    "source_repo": SITE,
    "framework": "nextjs",
    "count": len(entries),
    "assets": entries,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(manifest, f, indent=1)
print("manifest: %s (%d entries)" % (OUT, len(entries)))

if __name__ == "__main__":
    pass