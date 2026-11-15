"""Minimal reader for VizieR asu-tsv output: returns {table_name: [row dicts]} (header, units, dashes, rows)."""
import gzip
import sys


def _open(path):
    return gzip.open(path, "rt", encoding="utf8", errors="replace") if str(path).endswith(".gz") else open(path, encoding="utf8", errors="replace")


def read(path):
    out, name, cols, state = {}, None, None, 0
    for line in _open(path):
        line = line.rstrip("\n")
        if line.startswith("#Name:"):
            name, state = line.split(":", 1)[1].strip(), 1
            continue
        if line.startswith("#") or not line.strip():
            if not line.strip() and state == 3:
                state = 1
            continue
        if state == 1:
            cols, state = [c.strip() for c in line.split("\t")], 2
        elif state == 2:
            if line.startswith("-"):
                state = 3
        elif state == 3:
            out.setdefault(name, []).append(dict(zip(cols, [v.strip() for v in line.split("\t")])))
    return out


if __name__ == "__main__":
    for t, rows in read(sys.argv[1]).items():
        for r in rows:
            print(t, {k: v for k, v in r.items() if v and (len(sys.argv) < 3 or k in sys.argv[2:])})


def read_sections(path):
    """vizier_specific.txt layout: '## <source>' then header, units, dashes, rows (comments stripped)."""
    out, src, cols, state = {}, None, None, 0
    for line in open(path, encoding="utf8", errors="replace"):
        line = line.rstrip("\n")
        if line.startswith("## "):
            src, state = line[3:].strip(), 1
            continue
        if state == 1:
            cols, state = [c.strip() for c in line.split("\t")], 2
        elif state == 2 and line.startswith("-"):
            state = 3
        elif state == 3:
            if line.startswith("_r\t"):  # a second table of the same catalogue
                cols, state = [c.strip() for c in line.split("\t")], 2
                continue
            if not line.startswith("arcsec"):
                out.setdefault(src, []).append(dict(zip(cols, [v.strip() for v in line.split("\t")])))
    return out
