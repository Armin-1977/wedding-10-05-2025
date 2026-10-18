#!/usr/bin/env python3
"""Build a license-tracked catalog of 1970-1986 spoken-word audio from the Internet Archive.

Usage:  python3 build_catalog.py [--target 50] [--out catalog.csv]
Needs only the Python 3 standard library and normal internet access.

Every row records the item URL, the license URL the uploader set, the free-text
"rights" field, and a tier:
  A = machine-readable CC0 / Public Domain Mark / CC BY on the item
  B = U.S. government source (NASA/NARA etc.) -- usually public domain, verify per item
Anything else (CC BY-NC, ND, no license) is dropped. SA is dropped by default (--allow-sa).

IMPORTANT: the license field is whatever the UPLOADER chose. It does not prove they own the
rights. Treat every row as a lead to clear, not as cleared. Check the original rights holder,
and voice/likeness rights, before commercial use. Not legal advice.
"""
import argparse, csv, json, time, urllib.parse, urllib.request

THEMES = {
    "street_reporter":   ["street interview", "man on the street", "reporter on location", "eyewitness report"],
    "news_broadcast":    ["radio news broadcast", "television news audio", "newscast", "news bulletin"],
    "early_tech":        ["cellular telephone", "car phone", "personal computer", "home computer", "video game arcade", "compact disc", "videocassette recorder"],
    "crime_report":      ["crime report", "police news", "robbery news report", "courtroom report"],
    "aerobics_fitness":  ["aerobics", "jazzercise", "jogging craze", "fitness craze", "workout"],
    "space_gov":         ["space shuttle press briefing", "Apollo", "Skylab", "Voyager press conference"],
    "documentary_voice": ["documentary narration", "newsreel narration", "public service announcement"],
}
ALLOWED = ("publicdomain/zero", "publicdomain/mark", "/licenses/by/")
SA = "/licenses/by-sa/"
GOV_COLLECTIONS = {"nasa", "nara", "usgovernment", "fedflixarchive", "us_government"}
FIELDS = ["identifier", "title", "creator", "date", "licenseurl", "rights", "collection", "description"]

def search(query, rows=100, page=1):
    q = f'mediatype:audio AND date:[1970-01-01 TO 1986-12-31] AND ({query})'
    params = [("q", q), ("rows", rows), ("page", page), ("output", "json")] + [("fl[]", f) for f in FIELDS]
    url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)["response"]["docs"]

def tier(doc, allow_sa):
    lic = (doc.get("licenseurl") or "").lower()
    if lic:
        if any(a in lic for a in ALLOWED) or (allow_sa and SA in lic):
            return "A"
        return None
    cols = doc.get("collection") or []
    cols = [cols] if isinstance(cols, str) else cols
    return "B" if GOV_COLLECTIONS & {c.lower() for c in cols} else None

def flat(v):
    return "; ".join(v) if isinstance(v, list) else (v or "")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=50)
    ap.add_argument("--out", default="catalog.csv")
    ap.add_argument("--allow-sa", action="store_true")
    a = ap.parse_args()
    per_theme = max(3, a.target // len(THEMES) + 1)
    seen, rows = set(), []
    for theme, terms in THEMES.items():
        got = 0
        for term in terms:
            if got >= per_theme: break
            try:
                docs = search(f'"{term}"')
            except Exception as e:
                print(f"! {theme}/{term}: {e}"); continue
            for d in docs:
                t = tier(d, a.allow_sa)
                if not t or d["identifier"] in seen: continue
                seen.add(d["identifier"]); got += 1
                rows.append({
                    "theme": theme, "tier": t, "search_term": term,
                    "title": flat(d.get("title")), "creator": flat(d.get("creator")),
                    "date": flat(d.get("date"))[:10],
                    "source_url": f"https://archive.org/details/{d['identifier']}",
                    "license_url": d.get("licenseurl", ""), "rights_field": flat(d.get("rights")),
                    "collections": flat(d.get("collection")),
                    "checked_on": time.strftime("%Y-%m-%d"),
                    "clearance_status": "TODO",  # TODO / cleared / rejected
                    "clearance_notes": "",       # original rights holder, voice/likeness, music beds
                })
                if got >= per_theme: break
            time.sleep(1)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["theme"])
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows to {a.out}")

if __name__ == "__main__":
    main()
