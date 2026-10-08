#!/usr/bin/env python3
"""Locate the "notons" of the James Joyce Digital Archive in the text: the
phrases of Finnegans Wake that the archive links to the entries of Joyce's
notebooks (and notesheets, copybooks, ...) from which they come.

The archive's text of 1939 (src/rose/l39/SECTION.htm, fetched by fetch.sh)
has these phrases as anchors, named by the codes of their entries (e.g.
"n18185i": notebook N18, page 185, entry i). Clicking such a phrase on the
archive shows the entry in a popup, with its source and links to its usage
and drafts, for every notebook, also those whose full transcriptions the
archive does not publish. Its pages are aligned with the pages here (by the
page breaks of 1939 that it marks); every phrase gives a note linking to the
phrase on the archive's page, labelled with its entry ("N18 (VI.B.8):
185(i)"; the labels of the notebooks are in src/rose/notebooks.txt).

    notons.py COLLATION.json OUT.json

writes a list of [page, component, line, token, lemma, entry, url].
"""

import sys, os, re, json, difflib, collections
import html.parser
from urllib.parse import urljoin

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'src', 'rose')
CONTINUES = { 'pb' : 414, 'le' : 279 }

def notebooks():
    """Notebooks: code -> label (e.g. "n53" -> "N53 (VI.B.46)")."""
    out = {}
    for l in open(os.path.join(SRC, 'notebooks.txt'), encoding = 'utf-8'):
        if l.strip() and not l.startswith('#'):
            (code, label) = l.rstrip('\n').split(' ', 1)
            out[code] = label
    return out

class Parser(html.parser.HTMLParser):
    """The characters of a page: (page, character, link)."""
    def __init__(self, base, page):
        super().__init__(convert_charrefs = True)
        self.base, self.page = base, page
        self.on = False
        self.link = None
        self.green = 0
        self.skip = 0
        self.out = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'main':
            self.on = True
        if not self.on:
            return
        if tag in ('script', 'style'):
            self.skip += 1
        if tag == 'font' and a.get('color') == 'green':
            self.green += 1
        if tag == 'a' and 'fnbs/' in a.get('href', ''):
            self.link = urljoin(self.base, a['href'])
        if tag in ('p', 'br', 'div'):
            self.out.append((self.page, ' ', None))
    def handle_endtag(self, tag):
        if tag == 'main':
            self.on = False
        if not self.on:
            return
        if tag in ('script', 'style'):
            self.skip -= 1
        if tag == 'font' and self.green:
            self.green -= 1
        if tag == 'a':
            self.link = None
    def handle_data(self, data):
        if not self.on or self.skip:
            return
        if self.green:
            m = re.search(r'\{f39, *(\d+)\}', data)
            if m:
                self.page = int(m.group(1))
            return
        for c in data.replace('­', '').replace('º', ''):
            self.out.append((self.page, ' ' if c.isspace() else c, None if c.isspace() else self.link))

CODE = re.compile(r'^(n\d\d|c\d\d|sd\d|sh\d|sa|sb)(\d+|a\d\d|f\d\d|ffr|ffv|bfr|bfv)([a-z]+)$')
# Pages that are not numbered, as the archive names them.
PAGES = { 'ffr' : 'front flyleaf recto', 'ffv' : 'front flyleaf verso',
          'bfr' : 'back flyleaf recto', 'bfv' : 'back flyleaf verso' }

def entry(code, labels):
    """The label of an entry: "n18185i" -> "N18 (VI.B.8): 185(i)"."""
    m = CODE.match(code)
    if not m:
        return None
    (nb, page, item) = m.groups()
    label = labels.get(nb) or labels.get('ssa' if nb in ('sa', 'sb') else nb, nb.upper())
    if page.isdigit():
        page = str(int(page))
    elif page[0] == 'a':
        page = 'appendix ' + str(int(page[1:]))
    else:
        page = PAGES.get(page, page)
    return '{}: {}({})'.format(label, page, item)

def norm(w):
    return re.sub(r'[^\w]', '', w.replace('_', '')).lower()

def words(section):
    p = Parser('https://jjda.ie/f/flex/{0}/l39{0}.htm'.format(section), CONTINUES.get(section))
    p.feed(open(os.path.join(SRC, 'l39', section + '.htm'), encoding = 'utf-8', errors = 'replace').read())
    out, cur = [], []
    for (page, c, link) in p.out + [(None, ' ', None)]:
        if c == ' ':
            if cur:
                links = [l for (_, _, l) in cur if l]
                out.append((cur[0][0], ''.join(x for (_, x, _) in cur), links[0] if links else None))
            cur = []
        else:
            cur.append((page, c, link))
    return out

def run(collation):
    text = { int(p) : v for (p, v) in json.load(open(collation))['text'].items() }
    labels = notebooks()
    sections = [os.path.basename(s.strip())[:-6] for s in open(os.path.join(SRC, 'sections.txt')) if s.strip()]
    out = []
    stats = collections.Counter()
    for sec in sections:
        if sec == 'ln' or not os.path.exists(os.path.join(SRC, 'l39', sec + '.htm')):
            continue
        ws = words(sec)
        bypage = collections.defaultdict(list)
        for (i, (page, w, link)) in enumerate(ws):
            bypage[page].append(i)
        for (p, idx) in bypage.items():
            if p is None or p not in text:
                continue
            ours = []
            for comp in ('main', 'L', 'R', 'F'):
                for (k, l) in enumerate(text[p].get(comp, [])):
                    t = re.sub(r'\[\[img:[^\]]*\]\]\s*', '', l['t'])
                    for (n, w) in enumerate(t.split()):
                        ours.append((comp, k, n, w))
            a = [norm(ws[i][1]) for i in idx]
            b = [norm(w) for (_, _, _, w) in ours]
            where = {}
            for (tag, i1, i2, j1, j2) in difflib.SequenceMatcher(None, a, b, autojunk = False).get_opcodes():
                if tag == 'equal' or (tag == 'replace' and i2 - i1 == j2 - j1):
                    for k in range(i2 - i1):
                        where[idx[i1 + k]] = j1 + k
            # Runs of consecutive words with the same link are one phrase.
            k = 0
            while k < len(idx):
                i = idx[k]
                link = ws[i][2]
                if not link:
                    k += 1
                    continue
                run = [i]
                while k + 1 < len(idx) and ws[idx[k + 1]][2] == link:
                    k += 1
                    run.append(idx[k])
                k += 1
                code = link.split('#')[-1]
                label = entry(code, labels)
                stats['links'] += 1
                if label is None:
                    stats['unlabelled'] += 1
                    continue
                js = [where[i] for i in run if i in where]
                if not js:
                    stats['unplaced'] += 1
                    continue
                (comp, line, tok, _) = ours[js[0]]
                lemma = ' '.join(ours[j][3] for j in js if ours[j][:2] == (comp, line))
                url = 'https://jjda.ie/f/flex/{0}/l39{0}.htm#{1}'.format(sec, code)
                out.append([p, comp, line + 1, tok, lemma, label, url])
                stats['placed'] += 1
    print(dict(stats), file = sys.stderr)
    return out

if __name__ == '__main__':
    json.dump(run(sys.argv[1]), open(sys.argv[2], 'w'), ensure_ascii = False)
