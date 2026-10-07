#!/usr/bin/env python3
"""Crop lines of a page of the 1939 (F) or 1958 (V) scan for visual checking.

    crop.py [-v] PAGE LINE [CONTEXT]

LINE is the 1-based index of a main text line in Wilson's transcription; the
OCR line most similar to it is located and cropped with CONTEXT lines around.
Writes /tmp/fw-crop-PAGE-LINE.png and prints its name.
"""
import sys, subprocess, difflib, os
from witnesses import w_pages, SRC
from scans import f_pages, v_pages

def main():
    args = sys.argv[1:]
    v = args[0] == '-v'
    if v:
        args = args[1:]
    page, line = int(args[0]), int(args[1])
    ctx = int(args[2]) if len(args) > 2 else 1
    w = w_pages()[page]['main']
    target = w[min(line, len(w)) - 1]['t']
    s = (v_pages() if v else f_pages())[page]
    best = max(range(len(s['lines'])), key = lambda i: difflib.SequenceMatcher(None, target, s['lines'][i]['t']).ratio())
    lo, hi = max(0, best - ctx), min(len(s['lines']) - 1, best + ctx)
    top = min(s['lines'][i]['b'][1] for i in range(lo, hi + 1)) - 20
    bot = max(s['lines'][i]['b'][3] for i in range(lo, hi + 1)) + 20
    scale = 0.5 if not v else 0.6
    if v:
        # Viking scan: fetch the page image from archive.org.
        img = '/tmp/fw-v-{}.jpg'.format(s['scan'])
        if not os.path.exists(img):
            subprocess.run(['curl', '-sL', '-o', img, 'https://archive.org/download/finneganswake00joycuoft/page/n{}.jpg'.format(s['scan'])], check = True)
        out = '/tmp/fw-crop-v-{}-{}.png'.format(page, line)
        (W, H) = (s['w'], s['h'])
        subprocess.run(['convert', img, '-resize', '{}x{}!'.format(W, H), '-crop', '{}x{}+0+{}'.format(W, bot - top, top), '-resize', '{}%'.format(int(scale * 100)), out], check = True)
    else:
        dpi = 600 * scale
        out = '/tmp/fw-crop-{}-{}'.format(page, line)
        subprocess.run(['pdftoppm', '-f', str(s['scan'] + 1), '-l', str(s['scan'] + 1), '-r', str(int(dpi)), '-gray',
                        '-x', '0', '-y', str(int(top * scale)), '-W', str(int(s['w'] * scale)), '-H', str(int((bot - top) * scale)),
                        '-png', '-singlefile', os.path.join(SRC, 'f1939.pdf'), out], check = True)
        out += '.png'
    print(out)

main()
