#!/usr/bin/env python3
"""Map the OCR of the archive.org scans of Finnegans Wake to printed pages.

    F  Faber 1939, first edition, Digital Library of India scan
       (archive.org: in.ernet.dli.2015.207614), ABBYY OCR.
    V  Viking 1958, University of Toronto scan
       (archive.org: finneganswake00joycuoft), ABBYY OCR.

Lines are produced by djvu_lines.py. The result is a dictionary from the page
number to the list of lines of the page (without the page number), each line a
dictionary with the text ("t") and the bounding box ("b": left, top, right,
bottom), and the scan index ("scan").
"""

import json, os, re
from witnesses import SRC, PAGES

def number_line(l):
    return re.fullmatch(r'\d{1,3}', l['t'].strip()) is not None

def strip_numbers(lines, p):
    """Remove the page number, the printer's signature marks and other short
    noise below (or above) the text block."""
    out = [l for l in lines if not (number_line(l) and abs(int(l['t'].strip()) - p) <= 1)]
    if len(out) < 3:
        return out
    def noise(l, w):
        t = l['t'].strip()
        if re.search(r'j\.\s?w\.\s?p', t, re.I):
            return True                        # Printer's imprint.
        if len(t) >= 12:
            return False
        centred = l['b'][0] > 0.3 * w
        return centred or not re.search(r'[A-Za-z]{2}', t)
    w = max(l['b'][2] for l in out)
    while len(out) > 2 and noise(out[-1], w):
        out.pop()
    while len(out) > 2 and noise(out[0], w):
        out.pop(0)
    return out

def f_pages():
    scans = json.load(open(os.path.join(SRC, 'f1939_lines.json')))
    out = {}
    for p in PAGES:
        i = p + 6
        out[p] = { 'scan' : i, 'lines' : strip_numbers(scans[i]['lines'], p),
                   'w' : scans[i]['w'], 'h' : scans[i]['h'] }
    return out

def shingles(text):
    w = re.findall(r"[a-z]+", text.lower())
    return set(zip(w, w[1:], w[2:]))

def v_pages():
    """Map the scans to pages by their content: the scan of a page shares the
    most word trigrams with Wilson's transcription of the page."""
    from witnesses import w_pages
    scans = json.load(open(os.path.join(SRC, 'v1958_lines.json')))
    w = w_pages()
    wsh = { p : shingles(' '.join(l['t'] for k in ('main', 'L', 'R', 'F') for l in w[p][k])) for p in PAGES }
    index = {}
    for p in PAGES:
        for s in wsh[p]:
            index.setdefault(s, []).append(p)
    best = {}
    for (i, sc) in enumerate(scans):
        sh = shingles(' '.join(l['t'] for l in sc['lines']))
        if len(sh) < 5:
            continue
        votes = {}
        for s in sh:
            for p in index.get(s, []):
                votes[p] = votes.get(p, 0) + 1
        if not votes:
            continue
        p = max(votes, key = votes.get)
        score = votes[p] / len(sh)
        if score > 0.3 and (p not in best or best[p][1] < score):
            best[p] = (i, score)
    out = {}
    for (p, (i, score)) in best.items():
        out[p] = { 'scan' : i, 'lines' : strip_numbers(scans[i]['lines'], p),
                   'w' : scans[i]['w'], 'h' : scans[i]['h'] }
    return out

if __name__ == '__main__':
    f = f_pages()
    v = v_pages()
    print('F pages', len(f), 'V pages', len(v), 'V missing', sorted(set(PAGES) - set(v)))

def ii2_split(page):
    """Classify the OCR lines of a page of II.2 into the main text, left and
    right marginalia and footnotes, by their geometry. Returns a dictionary
    with keys 'main', 'L', 'R', 'F'; each a list of lines sorted by position."""
    lines = sorted(page['lines'], key = lambda l: (l['b'][1], l['b'][0]))
    W = page['w']
    out = { 'main' : [], 'L' : [], 'R' : [], 'F' : [] }
    if not lines:
        return out
    def width(l):
        return l['b'][2] - l['b'][0]
    # Main column: the left edge of the long lines.
    long = sorted(l['b'][0] for l in lines if width(l) > 0.35 * W)
    mainl = long[len(long) // 3] if long else min(l['b'][0] for l in lines)
    mainr = max(l['b'][2] for l in lines if width(l) > 0.35 * W) if long else W
    hs = sorted(l['b'][3] - l['b'][1] for l in lines if width(l) > 0.35 * W)
    h = hs[len(hs) // 2] if hs else 80
    rest = []
    for l in lines:
        (x0, y0, x1, y1) = l['b']
        if x1 < mainl - 0.02 * W:
            out['L'].append(l)
        elif x0 > mainr - 0.15 * W and (y1 - y0) < 0.6 * h and l['t'].upper() == l['t']:
            out['R'].append(l)
        else:
            rest.append(l)
    # Footnotes: the block at the bottom, after a gap larger than the line pitch.
    pitches = sorted(b['b'][1] - a['b'][1] for (a, b) in zip(rest, rest[1:]))
    pitch = pitches[len(pitches) // 2] if pitches else 100
    split = len(rest)
    for i in range(len(rest) - 1, 0, -1):
        gap = rest[i]['b'][1] - rest[i - 1]['b'][1]
        if gap > 1.45 * pitch:
            split = i
            break
    # Only a real footnote block: it starts with a footnote number.
    if split < len(rest):
        out['main'] = rest[:split]
        out['F'] = rest[split:]
    else:
        out['main'] = rest
    return out
