#!/usr/bin/env python3
"""Compare the printed words of the 1939 (Faber) and 1958 (Viking) scans.

The two printings come from the same plates, so a word that was not changed
looks the same in both. Every word of the established text is located in both
scans (through the word boxes of their OCR), the two images of the word are
normalised (binarised, trimmed to the ink, scaled to the same size, blurred)
and correlated.

    imgcmp.py COLLATION.json OUT.json

writes, for every page and component, the list of the words of the
established text with the correlation of their images ("s", missing if the
word could not be located in both scans) and the OCR readings ("F", "V").
"""

import sys, os, json, difflib
import numpy as np
import cv2
from witnesses import SRC, PAGES, II2
from scans import f_pages, v_pages
from collate import typo, ocr, key, tokens

def words(S):
    """The OCR words of a scan page with their boxes, in reading order."""
    out = []
    for l in sorted(S['lines'], key = lambda l: (l['b'][1], l['b'][0])):
        for (t, b) in zip(l['t'].split(), l.get('w', [])):
            out.append((t, b))
    return out

def norm(img):
    """Binarise, drop the ink of the neighbouring words (components touching
    the left or right edge of the crop), trim to the ink, scale to a fixed
    height."""
    if img is None or img.size == 0:
        return None
    _, bw = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(bw, 8)
    W = bw.shape[1]
    keep = np.zeros(n, bool)
    for k in range(1, n):
        (x, y, w, h, a) = stats[k]
        if x == 0 or x + w >= W or a < 4:
            continue
        keep[k] = True
    bw = np.where(keep[lab], 255, 0).astype(np.uint8)
    ys, xs = np.nonzero(bw)
    if len(xs) < 10:
        return None
    bw = bw[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h = 40
    w = max(4, int(round(bw.shape[1] * h / bw.shape[0])))
    return cv2.resize(bw, (w, h), interpolation = cv2.INTER_AREA)

def similarity(a, b):
    """Correlation of two normalised word images (1 is the same)."""
    if a is None or b is None:
        return None
    ra = a.shape[1] / a.shape[0]
    rb = b.shape[1] / b.shape[0]
    aspect = min(ra, rb) / max(ra, rb)
    b = cv2.resize(b, (a.shape[1], a.shape[0]), interpolation = cv2.INTER_AREA)
    a = cv2.GaussianBlur(a.astype(np.float32), (0, 0), 2.5)
    b = cv2.GaussianBlur(b.astype(np.float32), (0, 0), 2.5)
    a -= a.mean()
    b -= b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    if d == 0:
        return None
    return float((a * b).sum() / d) * aspect

def local(a, b):
    """The largest local difference of two normalised word images: the mean
    absolute difference of letter-sized windows, each compared at the best
    small horizontal shift (0 is the same, 1 is completely different)."""
    if a is None or b is None:
        return None
    b = cv2.resize(b, (a.shape[1], a.shape[0]), interpolation = cv2.INTER_AREA)
    a = cv2.GaussianBlur(a.astype(np.float32) / 255, (0, 0), 1.2)
    b = cv2.GaussianBlur(b.astype(np.float32) / 255, (0, 0), 1.2)
    h, w = a.shape
    win, step, sh = 16, 6, 4
    worst = 0.0
    for x in range(0, max(1, w - win + 1), step):
        wa = a[:, x:x + win]
        ink = wa.mean() + 1e-3
        best = None
        for d in range(-sh, sh + 1):
            if x + d < 0 or x + d + win > w:
                continue
            diff = np.abs(wa - b[:, x + d:x + d + win]).mean() / max(ink, b[:, x + d:x + d + win].mean() + 1e-3)
            best = diff if best is None else min(best, diff)
        if best is not None:
            worst = max(worst, best)
    return float(worst)

def crop(img, scale, box, pad = 5):
    (x0, y0, x1, y1) = [int(round(v * scale)) for v in box]
    return img[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad]

def union(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]

def locate(est, ws):
    """For every established token, the OCR words corresponding to it."""
    a = [key(t).lower() for t in est]
    b = [key(ocr(typo(t))).lower() for (t, _) in ws]
    out = [None] * len(est)
    for (tag, i1, i2, j1, j2) in difflib.SequenceMatcher(None, a, b, autojunk = False).get_opcodes():
        if tag == 'equal' or (tag == 'replace' and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                out[i1 + k] = [ws[j1 + k]]
        elif tag == 'replace' and i2 - i1 == 1:
            out[i1] = ws[j1:j2]
    return out

def page(p, text, F, V):
    fimg = cv2.imread(os.path.join(SRC, 'f1939-pages', 'p{}.png'.format(F[p]['scan'] + 1)), cv2.IMREAD_GRAYSCALE)
    vimg = cv2.imread(os.path.join(SRC, 'v1958-pages', 'n{}.jpg'.format(V[p]['scan'])), cv2.IMREAD_GRAYSCALE)
    fs = fimg.shape[1] / F[p]['w']
    vs = vimg.shape[1] / V[p]['w']
    fw, vw = words(F[p]), words(V[p])
    out = {}
    comps = [c for c in ('main', 'L', 'R', 'F') if text[str(p)].get(c)]
    est = []        # (component, line, token)
    for c in comps:
        for (i, l) in enumerate(text[str(p)][c]):
            if l['t'].startswith('[[img:'):
                continue
            for t in typo(l['t']).split():
                est.append((c, i, t))
    lf = locate([t for (_, _, t) in est], fw)
    lv = locate([t for (_, _, t) in est], vw)
    for (k, (c, i, t)) in enumerate(est):
        rec = { 't' : t }
        if lf[k]:
            rec['F'] = ' '.join(x for (x, _) in lf[k])
        if lv[k]:
            rec['V'] = ' '.join(x for (x, _) in lv[k])
        if lf[k] and lv[k]:
            na = norm(crop(fimg, fs, union([b for (_, b) in lf[k]])))
            nb = norm(crop(vimg, vs, union([b for (_, b) in lv[k]])))
            s = similarity(na, nb)
            if s is not None:
                rec['s'] = round(s, 3)
                rec['d'] = round(local(na, nb), 3)
                rec['fb'] = union([b for (_, b) in lf[k]])
                rec['vb'] = union([b for (_, b) in lv[k]])
        out.setdefault(c, {}).setdefault(i, []).append(rec)
    return out

def main():
    data = json.load(open(sys.argv[1]))
    F, V = f_pages(), v_pages()
    pages = [int(x) for x in sys.argv[3:]] or PAGES
    res = {}
    for p in pages:
        res[p] = page(p, data['text'], F, V)
    json.dump(res, open(sys.argv[2], 'w'))

if __name__ == '__main__':
    main()
