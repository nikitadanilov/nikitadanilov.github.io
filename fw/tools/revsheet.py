#!/usr/bin/env python3
"""Contact sheets for reviewing candidate variants by eye.

    revsheet.py REVIEW.json OUTPREFIX [PER-SHEET]

For every line in REVIEW.json (made from the output of reocr.py), the line
is cropped from the 1939 scan (above) and the 1958 scan (below), under a
label with the line reference and the suspect words (established text /
1939 reading / 1958 reading, as read by RapidOCR).
"""
import sys, os, json, difflib
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from witnesses import SRC
from scans import f_pages, v_pages
from collate import ocr_components
from witnesses import w_pages, t_pages

def best(lines, text):
    return max(lines, key = lambda l: difflib.SequenceMatcher(None, text, l['t'], autojunk = False).ratio())

def crop(img, scale, box, width):
    (x0, y0, x1, y1) = box
    h = y1 - y0
    top, bot = int((y0 - h * 0.35) * scale), int((y1 + h * 0.35) * scale)
    im = img[max(0, top):bot, :]
    im = cv2.resize(im, (width, int(im.shape[0] * width / im.shape[1])))
    return im

def main():
    rev = json.load(open(sys.argv[1]))
    prefix = sys.argv[2]
    per = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    F, V = f_pages(), v_pages()
    font = ImageFont.load_default()
    W = 1400
    sheets = [rev[i:i + per] for i in range(0, len(rev), per)]
    for (n, items) in enumerate(sheets):
        rows = []
        for it in items:
            p = it['page']
            fimg = cv2.imread(os.path.join(SRC, 'f1939-pages', 'p{}.png'.format(F[p]['scan'] + 1)), 0)
            vimg = cv2.imread(os.path.join(SRC, 'v1958-pages', 'n{}.jpg'.format(V[p]['scan'])), 0)
            fl = best(F[p]['lines'], it['text'])
            vl = best(V[p]['lines'], it['text'])
            a = crop(fimg, fimg.shape[1] / F[p]['w'], fl['b'], W)
            b = crop(vimg, vimg.shape[1] / V[p]['w'], vl['b'], W)
            ref = '{:03d}.{}{:02d}'.format(p, '' if it['comp'] == 'main' else it['comp'], it['line'])
            label = Image.new('L', (W, 16), 255)
            ImageDraw.Draw(label).text((4, 2), ref + '   ' + '   '.join('{} / {} / {}'.format(*w) for w in it['words']),
                                       fill = 0, font = font)
            rows += [np.array(label), a, b, np.full((5, W), 100, np.uint8)]
        sheet = np.vstack(rows)
        out = '{}-{:02d}.png'.format(prefix, n)
        cv2.imwrite(out, sheet)
        print(out, sheet.shape)

main()
