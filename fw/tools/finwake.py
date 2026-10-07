#!/usr/bin/env python3
"""Locate the glosses of finwake.com (https://finwake.com) in the text.

A gloss may be on a word, on several words, or on a part of a word (the
parts of the thunderwords, "tauf" in "tauftauf").

The chapters of finwake.com (src/finwake/tekstN.htm, fetched by fetch.sh)
are the text of the book with the glossed words linked to the glosses. The
words of each page are aligned with the words of the page of the established
text; every glossed word gives a note "finwake: LEMMA", the lemma linking to
the gloss.

    finwake.py COLLATION.json OUT.json

writes a list of [page, component, line, lemma, url]: line is 1-based in the
component, lemma is the glossed text as it is in the established line.
"""

import sys, os, re, json, html, difflib, collections
import html.parser
from urllib.parse import urljoin, quote

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'src', 'finwake')
CHAPTERS = [1, 2, 3, 4, 5, 6, 7, 8, 21, 22, 23, 24, 31, 32, 33, 34, 41]

class Parser(html.parser.HTMLParser):
    """The characters of a chapter: (page, character, link)."""
    def __init__(self, base):
        super().__init__(convert_charrefs = True)
        self.base = base
        self.page = None
        self.link = None
        self.out = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'a' and 'name' in a and a['name'].isdigit():
            self.page = int(a['name'])
        elif tag == 'a' and '#' in a.get('href', '') and a.get('target') != '_self':
            self.link = urljoin(self.base, a['href'])
        elif tag in ('dd', 'p', 'br', 'td', 'tr'):
            self.out.append((self.page, ' ', None))
    def handle_endtag(self, tag):
        if tag == 'a':
            self.link = None
    def handle_data(self, data):
        if self.page is None:
            return
        for c in data:
            self.out.append((self.page, ' ' if c.isspace() else c, self.link if not c.isspace() else None))

def norm(w):
    return re.sub(r'[^\w]', '', w.replace('_', '')).lower()

def chapter_words(n):
    """The words of a chapter: (page, word, [(link, part of the word)])."""
    p = Parser('https://finwake.com/1024chapter{}/'.format(n))
    p.feed(open(os.path.join(SRC, 'tekst{}.htm'.format(n)), encoding = 'latin-1').read())
    words, cur = [], []
    for (page, c, link) in p.out + [(None, ' ', None)]:
        if c == ' ':
            if cur:
                text = ''.join(x for (_, x, _) in cur)
                # The linked parts of the word: runs of characters with the
                # same link.
                parts, prev = [], None
                for (_, x, l) in cur:
                    if l is not None and l == prev:
                        parts[-1][1] += x
                    elif l is not None:
                        parts.append([l, x])
                    prev = l
                words.append((cur[0][0], text, [(l, x) for (l, x) in parts]))
            cur = []
        else:
            cur.append((page, c, link))
    return words

def anchors(words):
    """The glosses: (page, [indices of the words], url, text). A gloss on
    consecutive whole words spans them; a gloss on a part of a word is that
    part."""
    out = []
    for (i, (page, w, parts)) in enumerate(words):
        for (link, x) in parts:
            whole = norm(x) == norm(w)
            if whole and out and out[-1][2] == link and out[-1][1][-1] == i - 1 and out[-1][4]:
                out[-1][1].append(i)
                out[-1][3] += ' ' + x
            else:
                out.append([page, [i], link, x, whole])
    return [(p, wi, l, x) for (p, wi, l, x, _) in out]

def run(collation):
    text = { int(p) : v for (p, v) in json.load(open(collation))['text'].items() }
    words = []
    for n in CHAPTERS:
        words += chapter_words(n)
    bypage = collections.defaultdict(list)
    for (i, (page, w, parts)) in enumerate(words):
        bypage[page].append(i)
    glosses = collections.defaultdict(list)
    for a in anchors(words):
        glosses[a[0]].append(a)
    out = []
    lost = 0
    for (p, idx) in sorted(bypage.items()):
        if p not in text:
            continue
        ours = []     # (component, line, token)
        for comp in ('main', 'L', 'R', 'F'):
            for (k, l) in enumerate(text[p].get(comp, [])):
                for t in l['t'].split():
                    ours.append((comp, k, t))
        a = [norm(words[i][1]) for i in idx]
        b = [norm(t) for (_, _, t) in ours]
        where = {}
        for (tag, i1, i2, j1, j2) in difflib.SequenceMatcher(None, a, b, autojunk = False).get_opcodes():
            if tag == 'equal' or (tag == 'replace' and i2 - i1 == j2 - j1):
                for k in range(i2 - i1):
                    where[idx[i1 + k]] = j1 + k
        for (page, wi, url, gl) in glosses[p]:
            js = [where[i] for i in wi if i in where]
            if not js:
                lost += 1
                continue
            (comp, line, _) = ours[js[0]]
            js = [j for j in js if ours[j][:2] == (comp, line)]
            lemma = ' '.join(ours[j][2] for j in js)
            # The lemma is the glossed text: without the punctuation around it.
            core = re.sub(r'^[^\w]+|[^\w]+$', '', gl.replace('_', ''))
            plain = lemma.replace('_', '')
            if core and core in plain:
                lemma = core
            else:
                lemma = re.sub(r'^[^\w]+|[^\w]+$', '', plain) or plain
            # The position of the lemma among the tokens of the line, to tell
            # repeated words apart.
            first = js[0] - next(j for j in range(len(ours)) if ours[j][:2] == (comp, line))
            out.append([p, comp, line + 1, lemma, url, first])
    print('glosses located:', len(out), 'lost:', lost, file = sys.stderr)
    return out

GLOSSES = os.path.join(SRC, 'glosses')

def page_anchors(url):
    """The anchors (name and id attributes) of a gloss page, from its copy
    in src/finwake/glosses (fetched by fetch.sh), or None."""
    path = os.path.join(GLOSSES, url.split('#')[0][len('https://finwake.com/'):].replace('/', '_'))
    if not os.path.exists(path):
        return None
    t = open(path, encoding = 'latin-1').read()
    return [html.unescape(m.group(2)) for m in re.finditer(r'\b(name|id)\s*=\s*["\']([^"\']*)["\']', t, re.I)]

def repair(glosses):
    """finwake.com links some glosses to anchors that are not in the page
    (its links stop at the first blank of the name of the anchor). Link each
    such gloss to the anchor that the broken one is a part of, or to the one
    named after the lemma. Glosses whose anchor is nowhere in the page are
    not published on the free pages of finwake.com: they are dropped."""
    cache = {}
    counts = collections.Counter()
    out = []
    for g in glosses:
        (page, frag) = g[4].split('#', 1) if '#' in g[4] else (g[4], None)
        if page not in cache:
            cache[page] = page_anchors(page)
        names = cache[page]
        if frag is None or names is None or frag in names:
            out.append(g)
            continue
        lemma = g[3].replace('_', '')
        cands = [n for n in names if n.startswith(frag + ' ')] or \
                [n for n in names if n.lower() == frag.lower()] or \
                [n for n in names if norm(n) == norm(lemma)] or \
                [n for n in names if norm(n).startswith(norm(lemma)) and norm(lemma)]
        if cands:
            g[4] = page + '#' + quote(cands[0], safe = '')
            counts['repaired'] += 1
            out.append(g)
        else:
            counts['dropped'] += 1
    print('broken links repaired:', counts['repaired'], 'dropped:', counts['dropped'], file = sys.stderr)
    return out

if __name__ == '__main__':
    json.dump(repair(run(sys.argv[1])), open(sys.argv[2], 'w'), ensure_ascii = False)
