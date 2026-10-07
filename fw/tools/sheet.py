#!/usr/bin/env python3
"""Make a contact sheet of lines of the 1939 (F) and 1958 (V) scans, for
checking readings by eye.

    sheet.py OUT.png REF TEXT [REF TEXT...]

REF is a label (usually the page.line reference, starting with the page
number), TEXT is the text of the line (as established); the most similar OCR
line of the page is located and cropped (with half a line of context) from
both scans, one above the other.
"""
import sys, os, subprocess, difflib, re
from PIL import Image, ImageDraw, ImageFont
from witnesses import SRC
from scans import f_pages, v_pages

F, V = None, None

def locate(S, text):
    best = max(S['lines'], key = lambda l: difflib.SequenceMatcher(None, text, l['t'], autojunk = False).ratio())
    return best['b']

def crop_f(page, box, scale = float(os.environ.get("SCALE", "0.33"))):
    s = F[page]
    (x0, y0, x1, y1) = box
    h = y1 - y0
    top, bot = max(0, y0 - h // 2), min(s['h'], y1 + h // 2)
    out = '/tmp/fw-sheet-f.png'
    dpi = 600 * scale
    subprocess.run(['pdftoppm', '-f', str(s['scan'] + 1), '-l', str(s['scan'] + 1), '-r', str(dpi), '-gray',
                    '-x', '0', '-y', str(int(top * scale)), '-W', str(int(s['w'] * scale)), '-H', str(int((bot - top) * scale)),
                    '-png', '-singlefile', os.path.join(SRC, 'f1939.pdf'), out[:-4]], check = True)
    return Image.open(out).convert('L')

def crop_v(page, box, width):
    s = V[page]
    img = '/tmp/fw-v-{}.jpg'.format(s['scan'])
    if not os.path.exists(img):
        subprocess.run(['curl', '-sL', '-o', img,
                        'https://archive.org/download/finneganswake00joycuoft/page/n{}.jpg'.format(s['scan'])], check = True)
    im = Image.open(img).convert('L').resize((s['w'], s['h']))
    (x0, y0, x1, y1) = box
    h = y1 - y0
    im = im.crop((0, max(0, y0 - h // 2), s['w'], min(s['h'], y1 + h // 2)))
    return im.resize((width, int(im.height * width / im.width)))

def main():
    global F, V
    F, V = f_pages(), v_pages()
    out = sys.argv[1]
    args = sys.argv[2:]
    rows = []
    font = ImageFont.load_default()
    for (ref, text) in zip(args[::2], args[1::2]):
        page = int(re.match(r'\d+', ref).group(0))
        f = crop_f(page, locate(F[page], text))
        try:
            v = crop_v(page, locate(V[page], text), f.width)
        except Exception as e:
            v = Image.new('L', (f.width, 20), 255)
        label = Image.new('L', (f.width, 22), 255)
        ImageDraw.Draw(label).text((4, 4), ref + '   F=1939 above, V=1958 below', fill = 0, font = font)
        rows += [label, f, v, Image.new('L', (f.width, 6), 128)]
    W = max(r.width for r in rows)
    sheet = Image.new('L', (W, sum(r.height for r in rows)), 255)
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    sheet.save(out)
    print(out, sheet.size)

main()
