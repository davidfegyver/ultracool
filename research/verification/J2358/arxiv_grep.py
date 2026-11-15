"""Search arXiv (export API) for SPHEREx ultracool-dwarf papers and grep their HTML full text for J2358-5218 identifiers.

Run: nice -n 15 /home/paw/Desktop/ultracool/.venv/bin/python research/verification/J2358/arxiv_grep.py > arxiv_grep.txt
"""
import re
import time
import urllib.parse
import urllib.request

PATTERNS = ["2358-5218", "2358−5218", "235827", "23582773", "J2358", "189-203856", "6521791947874851968",
            "6521792325832957440", "359.616", "359.62"]
QUERIES = ['all:SPHEREx AND all:"brown dwarf"', 'all:SPHEREx AND all:"ultracool"', 'all:SPHEREx AND all:"L dwarf"',
           'all:SPHEREx AND all:"M dwarf"', 'all:"Backyard Worlds" AND all:companion',
           'all:"wide companion" AND all:"ultracool" AND all:Gaia']
UA = {"User-Agent": "ultracool-verification/1.0 (research script)"}


def get(url, t=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t).read().decode("utf8", "replace")


ids = {}
for q in QUERIES:
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": q, "start": 0, "max_results": 60, "sortBy": "submittedDate", "sortOrder": "descending"})
    entries = get(url).split("<entry>")[1:]
    print(f"### {q}: {len(entries)} entries")
    for e in entries:
        i = re.search(r"<id>http://arxiv.org/abs/([\d.]+)v\d+</id>", e).group(1)
        pub = re.search(r"<published>([^<]+)</published>", e).group(1)
        title = " ".join(re.search(r"<title>(.*?)</title>", e, re.S).group(1).split())
        if pub >= "2023-06":
            ids.setdefault(i, title)
            print(f"  {i} {pub[:10]} {title[:110]}")
    time.sleep(3)

print(f"\n### full-text grep of {len(ids)} papers (arxiv.org/html, falling back to /abs)")
for i, title in ids.items():
    try:
        txt = get(f"https://arxiv.org/html/{i}", 90)
        src = "html"
    except Exception as e:  # no HTML rendering: abstract only
        try:
            txt, src = get(f"https://arxiv.org/abs/{i}"), f"abs-only ({type(e).__name__})"
        except Exception as e2:
            print(f"{i}: FETCH FAILED {e2}")
            continue
    hits = sorted({p for p in PATTERNS if p in txt})
    print(f"{i} [{src}, {len(txt)} chars] hits={hits} :: {title[:90]}")
    time.sleep(2)
