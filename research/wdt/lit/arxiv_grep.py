"""Search arXiv (export API, title/abstract, 2019-2026) for WD + brown-dwarf companion papers and grep their full text
(arxiv.org/html, falling back to the PDF via pdfminer, then to the abstract page) for identifiers of
WD Gaia DR3 6350786278796634112 / WISE J235447.80-814044.9.

Run: nice -n 15 /home/paw/Desktop/ultracool/.venv/bin/python arxiv_grep.py > arxiv_grep.txt   (from research/wdt/lit/)
     ... arxiv_grep.py <id> [<id> ...] > arxiv_grep_extra.txt   (grep only the given ids, no API queries)
PDF fallback needs pdfminer.six's pdf2txt.py at /tmp/pdfv/bin (python3 -m venv /tmp/pdfv; /tmp/pdfv/bin/pip install pdfminer.six).
"""
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

# WD J2000 position 358.58088 -81.68471 -> J235419.4-814105; T dwarf J235447.8-814044.9
PATTERNS = ["2354-81", "2354−81", "2354–81", "2354$-$81", "235447", "235448", "235419", "235420", "J2354",
            "6350786278796634112", "358.58", "358.70", "358.69"]
QUERIES = [
    'abs:"white dwarf" AND abs:"brown dwarf" AND abs:wide',
    'abs:"white dwarf" AND abs:"brown dwarf" AND abs:companion',
    'abs:"white dwarf" AND abs:"T dwarf"',
    'abs:"white dwarf" AND abs:ultracool AND abs:companion',
    'abs:"white dwarf" AND abs:"ultracool" AND abs:binar*',
    'abs:COCONUTS',
    'abs:"Backyard Worlds" AND abs:"white dwarf"',
    'abs:benchmark AND abs:"brown dwarf" AND abs:"white dwarf"',
    'ti:"benchmark brown dwarfs"',
    'abs:magnetic AND abs:DZ AND abs:"white dwarf" AND abs:companion',
    'abs:"white dwarf" AND abs:"wide binar*" AND abs:"40 pc"',
]
# Papers that list the WD or the T dwarf (SIMBAD refs, simbad_bib.txt) or were named in the assignment.
EXPLICIT = {
    "1804.00362": "Tinney+2018 New Y and T dwarfs from WISE identified by methane imaging",
    "2011.11616": "Kirkpatrick+2021 20-pc census",
    "2106.07669": "Gentile Fusillo+2021 Gaia EDR3 WD catalogue",
    "2012.02061": "Gaia Collaboration 2021 GCNS",
    "2210.01608": "O'Brien+2023 Gaia WDs within 40 pc III (south)",
    "2312.02735": "O'Brien+2024 The 40 pc sample of white dwarfs from Gaia",
    "2401.15158": "Hernandez+2024 Rotation and magnetic fields in single WDs",
    "2308.05572": "Vincent+2024 XP classification of Gaia WDs",
    "2505.24560": "Zhang+2025 Benchmark brown dwarfs I",
    "2403.04592": "Rothermich+2024 89 new UCD companions (Backyard Worlds)",
}
UA = {"User-Agent": "ultracool-verification/1.0 (research script)"}
CAP = 60  # shortcut: query hits capped at 60 (newest first), raise if a query is saturated


def get(url, t=90):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t).read().decode("utf8", "replace")


ids = {a: "(given on command line)" for a in sys.argv[1:]} or dict(EXPLICIT)
for q in QUERIES if len(sys.argv) == 1 else []:
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": q, "start": 0, "max_results": CAP, "sortBy": "submittedDate", "sortOrder": "descending"})
    for attempt in range(3):
        try:
            entries = get(url).split("<entry>")[1:]
            break
        except Exception as e:
            print(f"  retry {q}: {e}")
            time.sleep(10)
    else:
        print(f"### {q}: QUERY FAILED")
        continue
    print(f"### {q}: {len(entries)} entries (relevant, 2019+ listed)")
    for e in entries:
        i = re.search(r"<id>https?://arxiv.org/abs/(\S+?)v\d+</id>", e).group(1)
        pub = re.search(r"<published>([^<]+)</published>", e).group(1)
        title = " ".join(re.search(r"<title>(.*?)</title>", e, re.S).group(1).split())
        s = (title + " " + re.search(r"<summary>(.*?)</summary>", e, re.S).group(1)).lower().replace("-", " ")
        # the API's abs: search is fuzzy; keep only WD + substellar/UCD papers, COCONUTS and the Benchmark-BD series
        rel = ("white dwarf" in s and any(k in s for k in ("brown dwarf", "ultracool", "t dwarf", "substellar", "l dwarf"))) \
            or "coconuts" in s or "benchmark brown dwarfs" in title.lower()
        if pub >= "2019" and rel:
            ids.setdefault(i, title)
            print(f"  {i} {pub[:10]} {title[:110]}")
    time.sleep(3)

print(f"\n### full-text grep of {len(ids)} papers (arxiv.org/html, falling back to PDF text, then /abs); patterns {PATTERNS}")
for i, title in ids.items():
    try:
        txt, src = get(f"https://arxiv.org/html/{i}"), "html"
    except Exception as e:  # no HTML rendering: PDF text, else abstract only
        try:
            pdf = f"/tmp/arxiv_{i.replace('/', '_')}.pdf"
            open(pdf, "wb").write(urllib.request.urlopen(urllib.request.Request(f"https://arxiv.org/pdf/{i}", headers=UA), timeout=120).read())
            txt = subprocess.run(["/tmp/pdfv/bin/pdf2txt.py", pdf], capture_output=True, text=True, timeout=600, check=True).stdout
            src = f"pdf-text (html {type(e).__name__})"
        except Exception as e1:
            try:
                txt, src = get(f"https://arxiv.org/abs/{i}"), f"abs-only (html {type(e).__name__}; pdf {type(e1).__name__})"
            except Exception as e2:
                print(f"{i}: FETCH FAILED {e2}")
                continue
    hits = {p: [txt[max(0, m.start() - 80):m.end() + 80].replace("\n", " ") for m in re.finditer(re.escape(p), txt)][:3]
            for p in PATTERNS if p in txt}
    print(f"{i} [{src}, {len(txt)} chars] hits={sorted(hits)} :: {title[:90]}")
    for p, ctx in hits.items():
        for c in ctx:
            print(f"    {p}: ...{re.sub(r'<[^>]+>', '', c)}...")
    time.sleep(2)
