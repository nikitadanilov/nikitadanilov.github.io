#!/usr/bin/env python3
"""The variants of the 2010 edition (Danis Rose and John O'Hanlon, eds.,
Finnegans Wake, Houyhnhnm Press, Mousehole, 2010; Penguin Classics, 2012).

The James Joyce Digital Archive (jjda.ie), the editors' own site, has for
every section of the book a page "1939 -> 2010" (src/rose/cmp/SECTION10.htm,
fetched by fetch.sh): the text of 1939 with every change of 2010 marked, the
1939 reading struck through, followed by the 2010 reading, between "(f39" and
"f10)", and with the page breaks of both editions, "{f39, N}" and "{f10, N}".

The 1939 text of each page is aligned with the text of the page here; each
change becomes a footnote on the line, at the words it affects, in the form

    lemma] SIGLA; reading SIGLA

where the lemma is the text here (that of 1958) and the readings are those of
1939 and 2010, as they differ.

    rose.py COLLATION.json OUT.json

writes a dictionary: "notes", a list of [page, component, line, token, lemma,
note text, 2010 text near the change]; "pages", for every page here, the
section page of the 2010 text on jjda.ie, the 2010 pages it spans and a few
words of the 2010 text at its start (to link to it).
"""

import sys, os, re, json, html, difflib, collections
import html.parser

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'src', 'rose')
JJDA = 'https://jjda.ie/f/flex/'

# Sections without page markers of 1939: the page they continue or are on.
CONTINUES = { 'pb10' : (414, 'main'), 'le10' : (279, 'F') }
SKIP = { 'ln10' }      # Editorial notes on II.2, not text.

class Parser(html.parser.HTMLParser):
    """The stream of a comparison page: ('t', text), ('chg', old, new),
    ('p39', page), ('p10', page)."""
    def __init__(self):
        super().__init__(convert_charrefs = True)
        self.out = []
        self.on = False          # In the text (after the key).
        self.depth = {}          # Open elements of interest.
        self.red = 0
        self.green = 0
        self.strike = 0
        self.black = 0
        self.inchg = False
        self.old = ''
        self.new = ''
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'main':
            self.on = True
        if not self.on:
            return
        if tag in ('script', 'style'):
            self.skip += 1
        if tag == 'font' and a.get('color') == 'red':
            self.red += 1
        elif tag == 'font' and a.get('color') == 'green':
            self.green += 1
        elif tag == 'font' and a.get('color') == 'black':
            self.black += 1
        if tag == 'span' and a.get('class') == 'striketext':
            self.strike += 1
        if tag in ('p', 'br', 'div') and not self.inchg:
            self.out.append(('t', ' '))
    def handle_endtag(self, tag):
        if not self.on:
            return
        if tag in ('script', 'style'):
            self.skip -= 1
        if tag == 'font':
            # Close the innermost open font (red, green or black).
            if self.red:
                self.red -= 1
            elif self.green:
                self.green -= 1
            elif self.black:
                self.black -= 1
        if tag == 'span' and self.strike:
            self.strike -= 1
        if tag == 'main':
            self.on = False
    def handle_data(self, data):
        if not self.on or self.skip:
            return
        data = data.replace('­', '')
        if self.red:
            if '(f39' in data:
                self.inchg, self.old, self.new = True, '', ''
            elif 'f10)' in data:
                self.out.append(('chg', self.old, self.new))
                self.inchg = False
            return
        if self.green:
            m = re.search(r'\{f(39|10), *(\d+)\}', data)
            if m:
                self.out.append(('p' + m.group(1), int(m.group(2))))
            return
        data = data.replace('º', '')      # Footnote markers of jjda.ie.
        if self.inchg:
            if self.strike:
                self.old += data
            elif self.black:
                self.new += data
            return
        self.out.append(('t', data))

def stream(section):
    p = Parser()
    p.feed(open(os.path.join(SRC, 'cmp', section + '.htm'), encoding = 'utf-8', errors = 'replace').read())
    return p.out

def norm(s):
    """Normalise the text of jjda.ie: blanks; its layout markers (|sh ... sh|
    and the arrows that mark the redistribution of dialogue)."""
    s = re.sub(r'\|sh|sh\|', ' ', s)
    s = re.sub(r'[⇐⇓⇒⇑]', ' ', s)
    return re.sub(r'\s+', ' ', s)

class Side:
    """The text of one edition built from a stream, with marks: for every
    change, its span; for every page break, its position."""
    def __init__(self):
        self.text = ''
        self.marks = []     # (position, kind, value)

def build(st):
    """The 1939 and the 2010 texts of a stream, and the changes: a list of
    (start, end in 1939, start, end in 2010)."""
    t39, t10 = Side(), Side()
    changes = []
    for item in st:
        if item[0] == 't':
            t39.text += item[1]
            t10.text += item[1]
        elif item[0] == 'chg':
            (old, new) = (norm(item[1]), norm(item[2]))
            if old.strip() == '⇒' or new.strip() == '⇒':
                continue        # A marker of moved text: the move is two changes.
            a39, a10 = len(t39.text), len(t10.text)
            t39.text += old
            t10.text += new
            changes.append((a39, len(t39.text), a10, len(t10.text)))
        elif item[0] == 'p39':
            t39.marks.append((len(t39.text), 'p', item[1]))
            t10.marks.append((len(t10.text), 'p39', item[1]))
        elif item[0] == 'p10':
            t10.marks.append((len(t10.text), 'p', item[1]))
            t39.marks.append((len(t39.text), 'p10', item[1]))
    return t39, t10, changes

def tokens(text):
    """Tokens of a text: (start, end)."""
    return [(m.start(), m.end()) for m in re.finditer(r'\S+', text)]

def key(w):
    return re.sub(r'[^\w]', '', w.replace('_', '').lower())

def our_tokens(page):
    """Tokens of a page here: (component, line, index in the line, token)."""
    out = []
    for comp in ('main', 'L', 'R', 'F'):
        for (i, l) in enumerate(page.get(comp, [])):
            t = re.sub(r'\[\[img:[^\]]*\]\]\s*', '', l['t'])
            for (k, w) in enumerate(t.split()):
                out.append((comp, i, k, w))
    return out

def run(collation):
    text = { int(p) : v for (p, v) in json.load(open(collation))['text'].items() }
    sections = [os.path.basename(s.strip())[:-4] for s in open(os.path.join(SRC, 'sections.txt')) if s.strip()]
    notes, pages = [], {}
    stats = collections.Counter()
    for sec in sections:
        if sec in SKIP:
            continue
        t39, t10, changes = build(stream(sec))
        lex = '{0}/lex{0}.htm'.format(sec[:-2])
        breaks = sorted((pos, v) for (pos, k, v) in t39.marks if k == 'p')
        start = CONTINUES.get(sec, (None, None))[0]
        def page_at(pos):
            p = start
            for (b, v) in breaks:
                if b <= pos:
                    p = v
            return p
        b10 = sorted((pos, v) for (pos, k, v) in t10.marks if k == 'p')
        def page10_at(pos):
            p = None
            for (b, v) in b10:
                if b <= pos:
                    p = v
            return p
        def to10(pos):
            """The position in 2010 of a position in 1939 outside changes."""
            d = 0
            for (a39, e39, a10, e10) in changes:
                if e39 <= pos:
                    d = e10 - e39
            return pos + d
        toks39 = tokens(t39.text)
        tpage = [page_at(s) for (s, e) in toks39]
        # Align the 1939 tokens of every page with the tokens here.
        where = {}      # Index of a 1939 token -> (page, index of the token here).
        ourtoks = {}
        byp = collections.defaultdict(list)
        for (i, p) in enumerate(tpage):
            byp[p].append(i)
        for (p, idx) in byp.items():
            if p is None or p not in text:
                continue
            ours = ourtoks[p] = our_tokens(text[p])
            a = [key(t39.text[toks39[i][0]:toks39[i][1]]) for i in idx]
            b = [key(w) for (_, _, _, w) in ours]
            for (tag, i1, i2, j1, j2) in difflib.SequenceMatcher(None, a, b, autojunk = False).get_opcodes():
                if tag == 'equal' or (tag == 'replace' and i2 - i1 == j2 - j1):
                    for k in range(i2 - i1):
                        where[idx[i1 + k]] = (p, j1 + k)
            stats['tokens'] += len(idx)
            # The pages of 2010 the page spans, and its first words in 2010.
            s10 = to10(toks39[idx[0]][0])
            e10 = to10(toks39[idx[-1]][1])
            first = page10_at(s10 + 1)
            if p not in pages:
                pages[p] = { 'jjda' : JJDA + lex, 'from' : first, 'to' : page10_at(e10),
                             'start' : ' '.join(t10.text[s10:s10 + 300].split()[:6]), 'text10' : '' }
            else:
                pages[p]['to'] = page10_at(e10)
            pages[p]['text10'] += ' ' + norm(t10.text[s10:e10])
        stats['aligned'] += len(where)
        # The 1939 tokens touched by every change.
        groups = []
        for (a39, e39, a10, e10) in changes:
            if t39.text[a39:e39].strip() == '1939' and t10.text[a10:e10].strip() == '2010 text':
                continue        # The key of the page.
            if a39 == e39:
                touch = [i for (i, (s, e)) in enumerate(toks39) if s <= a39 <= e][:1] or \
                        [i for (i, (s, e)) in enumerate(toks39) if e <= a39][-1:]
            else:
                touch = [i for (i, (s, e)) in enumerate(toks39) if s < e39 and e > a39]
                if not touch:   # A change of blanks only.
                    touch = [i for (i, (s, e)) in enumerate(toks39) if e <= a39][-1:] + \
                            [i for (i, (s, e)) in enumerate(toks39) if s >= e39][:1]
            if not touch:
                stats['unplaced'] += 1
                continue
            # Changes touching the same or adjacent tokens are one variant.
            if groups and touch[0] <= groups[-1]['hi'] + 1:
                g = groups[-1]
                g['hi'] = max(g['hi'], touch[-1])
                g['ch'].append((a39, e39, a10, e10))
            else:
                groups.append({ 'lo' : touch[0], 'hi' : touch[-1], 'ch' : [(a39, e39, a10, e10)] })
        for g in groups:
            touch = [i for i in range(g['lo'], g['hi'] + 1) if i in where]
            if not touch:
                stats['unplaced'] += 1
                continue
            (a39, _, a10, _) = g['ch'][0]
            (_, e39, _, e10) = g['ch'][-1]
            s, e = toks39[g['lo']][0], toks39[g['hi']][1]
            old = norm(t39.text[s:e]).strip()
            new = norm(t10.text[a10 - max(0, a39 - s):e10 + max(0, e - e39)]).strip()
            (p, j0) = where[touch[0]]
            ours = ourtoks[p]
            js = [where[i][1] for i in touch if where[i][0] == p]
            # Words broken at the end of a line here: the other half too.
            if js and re.search(r'\w-$', ours[js[-1]][3]) and js[-1] + 1 < len(ours):
                js.append(js[-1] + 1)
            if js and js[0] > 0 and ours[js[0] - 1][:2] != ours[js[0]][:2] and re.search(r'\w-$', ours[js[0] - 1][3]):
                js.insert(0, js[0] - 1)
            (comp, line, tok, _) = ours[js[0]]
            whole = ''
            for (n, j) in enumerate(js):
                w = ours[j][3]
                if n > 0:
                    joined = ours[js[n - 1]][:2] != ours[j][:2] and re.search(r'\w-$', whole)
                    whole = whole[:-1] if joined else whole + ' '
                whole += w
            first = ' '.join(ours[j][3] for j in js if ours[j][:2] == (comp, line))
            near = norm(t10.text[max(0, a10 - 60):e10 + 60]).strip()
            notes.append([p, comp, line + 1, tok, whole, old, new, near, JJDA + lex, first])
            stats['placed'] += 1
    print(dict(stats), file = sys.stderr)
    return { 'notes' : notes, 'pages' : pages }

if __name__ == '__main__':
    json.dump(run(sys.argv[1]), open(sys.argv[2], 'w'), ensure_ascii = False)
