#!/usr/bin/env python3
"""Extract the lines of an archive.org djvu.xml OCR file.

Output: JSON list of scan pages, each a list of lines, each line a dict with
the text ("t"), the bounding box (left, top, right, bottom) of the line ("b")
and the bounding boxes of its words ("w").
"""
import sys, json, re
import xml.etree.ElementTree as ET

def lines(path):
    pages = []
    for ev, el in ET.iterparse(path, events = ('end',)):
        if el.tag == 'OBJECT':
            page = []
            for line in el.iter('LINE'):
                words = []
                wboxes = []
                box = [10**9, 10**9, 0, 0]
                for w in line.iter('WORD'):
                    c = [int(x) for x in w.get('coords').split(',')[:4]]
                    # coords: left, bottom, right, top
                    box = [min(box[0], c[0]), min(box[1], c[3]), max(box[2], c[2]), max(box[3], c[1])]
                    words.append((w.text or '').strip())
                    wboxes.append([c[0], c[3], c[2], c[1]])
                if words:
                    page.append({ 't' : ' '.join(words), 'b' : box, 'w' : wboxes })
            pages.append({ 'w' : int(el.get('width')), 'h' : int(el.get('height')), 'lines' : page })
            el.clear()
    return pages

if __name__ == '__main__':
    json.dump(lines(sys.argv[1]), open(sys.argv[2], 'w'), ensure_ascii = False)
