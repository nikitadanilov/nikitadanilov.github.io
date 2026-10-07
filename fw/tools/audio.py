#!/usr/bin/env python3
"""Locate the beginnings of recorded readings of Finnegans Wake in the text.

The recordings are YouTube videos (src/audio/readings.txt: one per line,
"ID|CHAPTER|READER", CHAPTER is the chapter in which the reading starts);
their automatic English captions (src/audio/ID.en.vtt, fetched by fetch.sh)
are matched against the text of the chapter: the line where the first
captioned words best match is where the reading starts, and the time of the
first matched word is where the link points.

    audio.py COLLATION.json OUT.json

writes a list of [page, line, url, reader, part]: line is 1-based in the main
text of the page.
"""

import sys, os, re, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'src', 'audio')
sys.path.insert(0, HERE)
from mkdeck import CHAPTERS, chapter

def norm(w):
    return re.sub(r'[^a-z]', '', w.lower())

def captions(vid):
    """The captioned words: [(seconds, word)]."""
    out = []
    seen = set()
    path = os.path.join(SRC, vid + '.en.vtt')
    t = None
    for line in open(path, encoding = 'utf-8'):
        line = line.strip()
        m = re.match(r'(\d+):(\d+):(\d+)\.(\d+) -->', line)
        if m:
            t = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            continue
        if not line or t is None or '-->' in line or line.startswith(('WEBVTT', 'Kind:', 'Language:')):
            continue
        if '<' not in line:
            # Automatic captions repeat each line as plain text; keep only the
            # timed version.
            continue
        # Words with their own timestamps: <00:00:01.234><c> word</c>.
        parts = re.split(r'<(\d+):(\d+):(\d+)\.\d+>', line)
        cur = t
        k = 0
        while k < len(parts):
            text = re.sub(r'<[^>]+>', '', parts[k])
            for w in text.split():
                if (cur, w, len(out)) not in seen:
                    out.append((cur, w))
            if k + 3 < len(parts):
                cur = int(parts[k + 1]) * 3600 + int(parts[k + 2]) * 60 + int(parts[k + 3])
            k += 4
    return out

def start(text, chap, caps, n = 40):
    """The (page, line, seconds) where the reading starts: the place in the
    chapter (or the following one) where the first n captioned words that are
    words of the text match best."""
    pages = sorted(p for p in text if chapter(p) in chap)
    toks = []
    for p in pages:
        for (i, l) in enumerate(text[p]['main']):
            for w in l['t'].split():
                if norm(w):
                    toks.append((p, i, norm(w)))
    vocab = set(w for (_, _, w) in toks)
    cw = [(s, norm(w)) for (s, w) in caps if norm(w) in vocab][:n]
    words = [w for (_, w) in cw]
    best, where = -1, 0
    W = 2 * n
    for i in range(0, max(1, len(toks) - W)):
        window = collections.Counter(w for (_, _, w) in toks[i:i + W])
        score = sum(min(c, window[w]) for (w, c) in collections.Counter(words).items())
        if score > best:
            best, where = score, i
    # The first run of at least two caption words matching the text in order
    # gives the place and the time.
    import difflib
    lo = max(0, where - n)
    window = [w for (_, _, w) in toks[lo:where + W]]
    sm = difflib.SequenceMatcher(None, words, window, autojunk = False)
    for b in sm.get_matching_blocks():
        if b.size >= 2:
            (p, i, _) = toks[lo + b.b]
            return (p, i + 1, cw[b.a][0], best)
    return None

def run(collation):
    text = { int(p) : v for (p, v) in json.load(open(collation))['text'].items() }
    order = [c for (c, _) in CHAPTERS]
    out = []
    for line in open(os.path.join(SRC, 'readings.txt'), encoding = 'utf-8'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        (vid, chap, reader, part) = [x.strip() for x in line.split('|')]
        nxt = order[min(order.index(chap) + 1, len(order) - 1)]
        r = start(text, (chap, nxt), captions(vid))
        if r is None:
            print('not located:', vid, file = sys.stderr)
            continue
        (p, i, s, score) = r
        url = 'https://www.youtube.com/watch?v={}&t={}s'.format(vid, max(0, s - 1))
        out.append([p, i, url, reader, part])
        print('{:03d}.{:02d} {:5d}s score {:2d} {} {}'.format(p, i, s, score, reader, part), file = sys.stderr)
    return out

if __name__ == '__main__':
    json.dump(run(sys.argv[1]), open(sys.argv[2], 'w'), ensure_ascii = False)
