#!/usr/bin/env python3
"""Candidate differences between the 1939 and 1958 printings, from the
output of imgcmp.py: the words whose OCR readings in the two scans differ in
a way not explained by the usual OCR confusions, or whose images differ.

    candidates.py IMGCMP.json OUT.json
"""
import sys, json, collections
from ocrnoise import ocr_like
from collate import key, typo, ocr

def k(x):
    return key(ocr(typo(x))).lower()

def classify(r):
    F, V, t = r.get('F'), r.get('V'), r['t']
    if not F or not V or k(F) == k(V):
        return None
    if ocr_like(k(V), k(F)) and ocr_like(k(F), k(V)):
        return 'shape' if r.get('s', 1) < 0.6 else None
    if k(V) == k(t):
        return '1939'
    if k(F) == k(t):
        return '1958'
    return 'neither'

def main():
    d = json.load(open(sys.argv[1]))
    out = []
    for (p, pg) in d.items():
        for (c, ls) in pg.items():
            for (i, l) in ls.items():
                for (j, r) in enumerate(l):
                    cls = classify(r)
                    if cls:
                        out.append(dict(r, page = int(p), comp = c, line = int(i) + 1, cls = cls))
    out.sort(key = lambda r: (r['page'], ['main', 'L', 'R', 'F'].index(r['comp']), r['line']))
    json.dump(out, open(sys.argv[2], 'w'), ensure_ascii = False)
    print(collections.Counter(r['cls'] for r in out))

main()
