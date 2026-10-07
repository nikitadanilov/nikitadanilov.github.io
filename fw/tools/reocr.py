#!/usr/bin/env python3
"""Read the candidate words (candidates.py) again in both scans with one OCR
engine (RapidOCR), so that the two images of a word are read the same way:
identical print is (nearly always) read identically.

Runs in a Python environment with rapidocr_onnxruntime installed:

    reocr.py CANDIDATES.json OUT.json
"""
import sys, os, json
import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'src')
LINES = { 'F' : json.load(open(os.path.join(SRC, 'f1939_lines.json'))),
          'V' : json.load(open(os.path.join(SRC, 'v1958_lines.json'))) }

def scans():
    # The scan indices of the pages, as computed by scans.py.
    return json.load(open(os.path.join(HERE, 'scanmap.json')))

def crop(img, scale, box, pad):
    (x0, y0, x1, y1) = [int(round(v * scale)) for v in box]
    h = y1 - y0
    return img[max(0, y0 - h // 3):y1 + h // 3, max(0, x0 - pad):x1 + pad]

def main():
    cands = json.load(open(sys.argv[1]))
    sm = scans()
    eng = RapidOCR()
    out = []
    cache = {}
    def image(which, p):
        k = (which, p)
        if k not in cache:
            cache.clear()
            if which == 'F':
                path = os.path.join(SRC, 'f1939-pages', 'p{}.png'.format(sm['F'][str(p)] + 1))
            else:
                path = os.path.join(SRC, 'v1958-pages', 'n{}.jpg'.format(sm['V'][str(p)]))
            img = cv2.imread(path)
            cache[k] = (img, img.shape[1] / LINES[which][sm[which][str(p)]]['w'])
        return cache[k]
    for c in cands:
        if 'fb' not in c:
            out.append(dict(c, rF = None, rV = None))
            continue
        res = {}
        for (which, box) in (('F', c['fb']), ('V', c['vb'])):
            (img, scale) = image(which, c['page'])
            im = crop(img, scale, box, 4)
            # Scale to a common height for the recogniser.
            im = cv2.resize(im, (max(8, int(im.shape[1] * 64 / im.shape[0])), 64))
            r, _ = eng(im, use_det = False, use_cls = False, use_rec = True)
            res[which] = r[0][0] if r else ''
        out.append(dict(c, rF = res['F'], rV = res['V']))
    json.dump(out, open(sys.argv[2], 'w'), ensure_ascii = False)

main()
