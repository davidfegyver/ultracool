"""Minimal VizieR asu-tsv reader: rows as dicts of stripped strings."""
def rows(f):
    L = [l.rstrip('\n') for l in open(f) if not l.startswith('#') and l.strip()]
    if not L: return []
    h = L[0].split('\t')
    return [dict(zip(h, [x.strip() for x in l.split('\t')])) for l in L[3:]]
