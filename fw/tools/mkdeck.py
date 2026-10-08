#!/usr/bin/env python3
"""Generate the card deck of Finnegans Wake from the collated text.

    mkdeck.py COLLATION.json OUTDIR

Writes one cardfile per chapter (I.1.deck ... IV.deck) into OUTDIR. Each
printed page is a card ("p003" ... "p628") in the "pages" series, tagged with
its chapter. Each printed line is a fragment whose identifier is its line
number by Fweet's rules, so that the line 3.04 is the fragment "p003-04", and
can be linked to as "!p003-04". In II.2 the footnotes and the left and right
marginalia are fragments "F01", "L01", "R01"... A verse continued on another
line with a hanging indent keeps its number: the continuation lines are
"07-1", "07-2"...
"""

import sys, os, json, re, collections
import variants
from scans import f_pages, v_pages

CHAPTERS = [ ('I.1', 3), ('I.2', 30), ('I.3', 48), ('I.4', 75), ('I.5', 104), ('I.6', 126), ('I.7', 169),
             ('I.8', 196), ('II.1', 219), ('II.2', 260), ('II.3', 309), ('II.4', 383), ('III.1', 403),
             ('III.2', 429), ('III.3', 474), ('III.4', 555), ('IV', 593) ]

def chapter(p):
    return [c for (c, start) in CHAPTERS if start <= p][-1]

def book(p):
    return chapter(p).split('.')[0]

F_ITEM = 'in.ernet.dli.2015.207614'
V_ITEM = 'finneganswake00joycuoft'

def image(item, scan):
    return 'https://archive.org/download/{}/page/n{}.jpg'.format(item, scan)

def exact(raw, rx):
    """A regular expression matching, in raw (the text of a line, with "_"
    for italics), exactly the part matched by rx in the text without the
    italics, and nowhere else."""
    plain, where = '', []
    for (i, c) in enumerate(raw):
        if c != '_':
            plain += c
            where.append(i)
    m = re.search(rx, plain)
    if not m or m.end() == m.start():
        return rx
    return unique(raw, where[m.start()], where[m.end() - 1] + 1) or rx

def unique(raw, a, b):
    """A regular expression matching the part [a, b) of raw (the text of a
    line, with "_" for italics) and nowhere else in it: card attaches a note
    to every match. Text following the part is added as a lookahead until
    the match is unique. None if it cannot be made unique."""
    rx = re.escape(raw[a:b])
    def matches(r):
        return [m.start() for m in re.finditer(r, raw)]
    for k in range(b, len(raw) + 1):
        r = rx + ('(?={})'.format(re.escape(raw[b:k])) if k > b else '')
        if matches(r) == [a]:
            return r
    r = rx + '(?={}$)'.format(re.escape(raw[b:]))
    return r if matches(r) == [a] else None

def locate(raw, lemma, token):
    """The span of raw (with "_" for italics) of the lemma (without them)
    found at or after the token with the given index. None if not found."""
    plain, where = '', []
    for (i, c) in enumerate(raw):
        if c != '_':
            plain += c
            where.append(i)
    starts = [m.start() for m in re.finditer(r'\S+', plain)]
    s = starts[token] if token < len(starts) else 0
    i = plain.find(lemma, s)
    if i < 0:
        i = plain.find(lemma)
    if i < 0:
        return None
    return (where[i], where[i + len(lemma) - 1] + 1)

FINWAKE = collections.defaultdict(list)   # (page, component, line) -> [(lemma, url, token)].

# Notes linking to finwake.com start with the letter tet.
FINWAKE_LETTER = '\u05d8'

def finwake(key, raw):
    """Notes linking the glossed words of the line to finwake.com."""
    out = []
    for (lemma, url, token) in FINWAKE.get(key, []):
        span = locate(raw, lemma, token)
        if span is None:
            continue
        rx = unique(raw, *span)
        if rx is None:
            continue
        rx = rx.replace('"', '.')
        out.append('/ +* "{}" {} {}'.format(rx, FINWAKE_LETTER + LRM, lemma))
        out.append(': += . "(?<={} ).+" -> '.format(FINWAKE_LETTER + LRM) + url.replace('{', '{{').replace('}', '}}'))
    return out

# The Hebrew letters that start the notes are right-to-left: a left-to-right
# mark after the letter keeps what follows (often digits) from being laid out
# right to left with it.
LRM = '\u200e'

# Notes linking to the notebook entries of the James Joyce Digital Archive
# start with a capital omega (distinct from the Hebrew letters of the other
# notes; left-to-right, so no mark is needed after it).
NOTON_LETTER = '\u03a9'
NOTONS = collections.defaultdict(list)  # (page, component, line) -> [(lemma, notebook, url, token)].

def notons(key, raw):
    """Notes linking phrases of the line to the notebook entries they come from."""
    out = []
    for (lemma, nb, url, token) in NOTONS.get(key, []):
        span = locate(raw, dashes(lemma).replace('_', ''), token)
        if span is None:
            continue
        rx = unique(raw, *span)
        if rx is None:
            continue
        out.append('/ +* "{}" {} {}: {}'.format(rx.replace('"', '.'), NOTON_LETTER, dashes(lemma).replace('_', ''), nb))
        out.append(': += . "(?<=: ){}$" -> {}'.format(re.escape(nb), url))
    return out

# Notes linking to recorded readings start with the letter qof ("qol", voice).
AUDIO_LETTER = '\u05e7'
AUDIO = collections.defaultdict(list)   # (page, line) -> [(url, reader, part)].

def audio(key, raw):
    """Notes linking the line where a recorded reading starts to it."""
    out = []
    for (url, reader, part) in AUDIO.get(key, []):
        first = raw.split()[0] if raw.split() else raw
        span = locate(raw, first.replace('_', ''), 0)
        if span is None:
            continue
        rx = unique(raw, *span)
        if rx is None:
            continue
        out.append('/ +* "{}" {} {}: {}'.format(rx.replace('"', '.'), AUDIO_LETTER + LRM, reader, part))
        out.append(': += . "(?<={} ).+" -> '.format(AUDIO_LETTER + LRM) + url)
        out.append(': place foot')
    return out

# Variorum notes start with the letter beth ("v" for variorum), to tell them
# from the other marginalia.
VARIORUM = '\u05d1'

ROSE = collections.defaultdict(list)    # (page, component, line) -> variants of 2010.
ROSE_PAGES = {}
MAXQUOTE = 12   # Longer readings of 2010 are abbreviated (and linked to jjda.ie).

def vkey(s):
    """Comparison key of readings: no italics, blanks, dash forms or soft
    breaks."""
    return re.sub(r'\s+', '', dashes(s).replace('_', '').replace('\u00ad', ''))

def vwords(s):
    """Words of a text for comparison: no italics, dash forms, case."""
    return ' '.join(dashes(s).replace('_', '').replace('\u00ad', '').split())

def fragment_url(url, near):
    """A link to the passage of the page url (on jjda.ie) containing the text
    near: a text fragment of a few words of it."""
    from urllib.parse import quote
    words = near.split()
    if len(words) > 8:
        words = words[len(words) // 2 - 4:len(words) // 2 + 4]
    return url + '#:~:text=' + quote(' '.join(words), safe = '')

def apparatus(ref, text, key = None):
    """The variant notes (footnotes) of the line ref with the given text:
    those of 1939 and 1958, and those of 2010. Note regular expressions cannot
    contain double quotes."""
    out = []
    text = re.sub(r'^\[\[img:[^\]]*\]\]\s*', '', text)    # A figure: its caption.
    if not text:
        return out
    rose = ROSE.get(key or parse_ref(ref), [])
    known = variants.notes(ref, text)
    for (rx, note) in known:
        # The reading of 2010 at a difference of 1939 and 1958: jjda.ie records
        # only the changes of 2010, so where it has none, 2010 keeps 1939.
        m = re.match(r'(.*)\] (1939|1958); (.*) (1939|1958)$', note)
        if m:
            (lemma, s1, reading, s2) = m.groups()
            # Which of the two readings the text of 2010 of the page has.
            t10 = ' ' + vwords(ROSE_PAGES.get(key[0] if key else parse_ref(ref)[0], {}).get('text10', '')) + ' '
            r58, r39 = (lemma, reading) if s1 == '1958' else (reading, lemma)
            in58, in39 = (' ' + vwords(r58) + ' ') in t10, (' ' + vwords(r39) + ' ') in t10
            agrees = '1958' if in58 and not in39 else '1939' if in39 and not in58 else None
            if agrees == s1:
                note = '{}] {} 2010; {} {}'.format(lemma, s1, reading, s2)
            elif agrees == s2:
                note = '{}] {}; {} {} 2010'.format(lemma, s1, reading, s2)
        out.append('/ +* "{}" {} {}'.format(exact(text, rx).replace('"', '.'), VARIORUM + LRM, note))
        out.append(': place foot')
    for r in rose:
        whole, new = dashes(r['whole']), dashes(r['new'])
        if vkey(whole) == vkey(new):
            continue    # 2010 agrees with this text (and differs only from jjda.ie's 1939).
        span = locate(text, dashes(r['first']).replace('_', ''), r['token'])
        if span is None:
            continue
        rx = unique(text, *span)
        if rx is None:
            continue
        overlap = any(vkey(note.split(']')[0]) in vkey(whole) for (_, note) in known)
        sigla = '1958' if overlap else '1939 1958'
        words = new.split()
        link = None
        if len(words) > MAXQUOTE and len(words) > len(whole.split()) + 3:
            new = '{} … {} ({} words)'.format(' '.join(words[:5]), ' '.join(words[-3:]), len(words))
            link = fragment_url(r['url'], r['near'])
        reading = new if new else 'om.'
        out.append('/ +* "{}" {} {}] {}; {} 2010'.format(rx.replace('"', '.'), VARIORUM + LRM,
                                                      whole.replace('_', ''), sigla, reading.replace('_', '')))
        if link:
            out.append(': += . "\\(\\d+ words\\)" -> ' + link.replace('{', '{{').replace('}', '}}'))
        out.append(': place foot')
    return out

def parse_ref(ref):
    (p, rest) = ref.split('.')
    comp = 'main' if rest[0].isdigit() else rest[0]
    return (int(p), comp, int(rest.lstrip('LRF')))

SUP = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')
# A footnote mark of II.2: one or two digits after a word or punctuation
# (not in "17:69", "4.32" or "A.1.").
MARK = re.compile(r'(?<![\d][.:])(?<!\d\\[.:])(?<!\b[A-Z]\.)(?<!\b[A-Z]\\\.)(?<=[^\s\d\\("])\d{1,2}(?=[\s,.;:!?)\]"\\]|$)')

def marks(line):
    """Raise the footnote marks of II.2 in a line of a cardfile: text lines,
    and the lemmas and regular expressions of notes. The number that starts
    a footnote is raised too."""
    if line.startswith('|'):
        body = line[1:]
        body = re.sub(r'^\d{1,2}(?= )', lambda m: m.group(0).translate(SUP), body)
        return '|' + MARK.sub(lambda m: m.group(0).translate(SUP), body)
    if line.startswith('/ +* "') and NOTON_LETTER in line:
        # A note of a notebook: the entry ("notebook: page(item)", after the
        # last but one ": ") is not text.
        m = re.search(r': [^:]*: [^:]*$', line)
        (head, label) = (line[:m.start()], line[m.start():])
        return MARK.sub(lambda m: m.group(0).translate(SUP), head) + label
    if line.startswith('/ +* "'):
        line = re.sub(r'^(/ \+\* ")(\d{1,2})(?=\\ )', lambda m: m.group(1) + m.group(2).translate(SUP), line)
        return MARK.sub(lambda m: m.group(0).translate(SUP), line)
    return line

def dashes(t):
    """The text has "--" for the em dash (as the transcriptions have it)."""
    return t.replace('--', '\u2014')

def balance(lines):
    """Make the italics ("_") of each line self-contained: close an italic
    span open at the end of a line and reopen it at the start of the next."""
    out = []
    italic = False
    for t in lines:
        n = t.count('_')
        s = ('_' if italic else '') + t
        italic = italic ^ (n % 2 == 1)
        if italic:
            s = s + '_'
        s = s.replace('__', '')
        out.append(s)
    return out

# The layout of the lines is not in the decks but in a generated style sheet
# (layout.conf): card writes the anchor of a fragment just before it, so
# a[name="p004-17"] + p selects the line 4.17. The lists of the lines that
# need something other than the default (justified) are collected here.
RAGGED = []     # Lines not set to the full measure.
INDENT = []     # Lines starting a paragraph.
CENTER = []     # Centred lines.

def fragment(fid, text, notes = [], image_width = '100%'):
    out = []
    m = re.match(r'\[\[img:([^\]]+)\]\]\s*(.*)$', text)
    if m:
        out.append('; img')
        out.append('/ url img/' + m.group(1))
        out.append('/ width ' + image_width)
        out.append('/ id ' + fid)
        if m.group(2):
            out.append('|' + m.group(2))
            out += notes
        return out + ['']
    out.append('|' + text)
    out.append('/ id ' + fid)
    out += notes
    return out + ['']

def classify(anchor, line, center = None):
    """Record the layout of the line with the given anchor."""
    if line.get('center') if center is None else center:
        CENTER.append(anchor)
    else:
        if not line.get('full'):
            RAGGED.append(anchor)
        if line.get('p'):
            INDENT.append(anchor)

def ids(lines):
    """Fweet line numbers of the main text lines."""
    out = []
    n, k = 0, 0
    for l in lines:
        if l.get('cont'):
            k += 1
            out.append('{:02d}-{}'.format(n, k))
        else:
            n += 1
            k = 0
            out.append('{:02d}'.format(n))
    return out

COLUMN = 590    # The width of the column (px), see fw.conf.

FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'fonts')
SIZE = { 'main' : 20, 'F' : 15 }   # Font sizes (px), see layout().

def rendered(text, size):
    """The width (px) of a line of text (with "_" for italics) in the text
    face, as a browser renders it (PIL measures about 3% narrower, because of
    the optical size)."""
    from PIL import ImageFont
    faces = [ImageFont.truetype(os.path.join(FONTS, f), size) for f in ('SourceSerif4.ttf', 'SourceSerif4-Italic.ttf')]
    w = sum(faces[k % 2].getlength(s) for (k, s) in enumerate(text.split('_')))
    return 1.03 * w

def measures(text):
    """The width (px) of the measure of each component of each page whose
    measure in the scans is narrower than that of the regular pages: the
    width of its widest full line in the text face. Other components fill
    the column."""
    out = {}
    for (p, pg) in text.items():
        for (comp, r) in pg.get('measure', {}).items():
            if r < 0.95 or comp == 'F':
                ws = [rendered(l['t'], SIZE[comp]) for l in pg.get(comp, []) if l.get('full')]
                if ws:
                    out[(p, comp)] = min(COLUMN, int(max(ws)) + 2)
    return out

MEASURE = {}

def card(p, page, first, F, V):
    out = card_lines(p, page, first, F, V)
    if not 260 <= p <= 308:
        return out
    res, head = [], False
    for l in out:
        head = head or l == '; head'
        res.append(l if head else marks(l))
        if l == '':
            head = False
    return res

def card_lines(p, page, first, F, V):
    out = []
    main = page['main']
    out.append('// name Page {}'.format(p))
    out.append('// id p{:03d}'.format(p))
    out.append('// +# book {:03d}'.format(p))
    out.append('// +# {} {:03d}'.format(book(p), p))
    if chapter(p) != book(p):
        out.append('// +# {} {:03d}'.format(chapter(p), p))
    brief = dashes(re.sub(r'\[\[img:[^\]]*\]\]\s*', '', main[0]['t']).replace('_', '')) if main else ''
    out.append('// brief {}: {}'.format(chapter(p), brief))
    out.append('')
    if first:
        out += ['; head', '/ level 3', '/ id chapter', '|' + chapter(p), '']
    texts = balance([dashes(l['t']) for l in main])
    margins = {}
    for comp in ('L', 'R'):
        mt = balance([dashes(l['t']) for l in page.get(comp, [])])
        # Marginal lines are set closer than the main text: a block of them
        # is anchored at the main line next to its first line, and its lines
        # are stacked there.
        start, k = None, 0
        for (i, l) in enumerate(page.get(comp, [])):
            at = l.get('at', 0)
            if start is None or at > start + 0.7 * k + 1:
                start, k = at, 0
            k += 1
            margins.setdefault(start, []).append((comp, '{}{:02d}'.format(comp, i + 1), mt[i]))
    pid = 'p{:03d}'.format(p)
    for (i, (fid, l)) in enumerate(zip(ids(main), main)):
        for (comp, mid, t) in margins.get(i, []):
            out += fragment(mid, t, notes = apparatus('{:03d}.{}'.format(p, mid), t) + finwake((p, mid[0], int(mid[1:])), t) + notons((p, mid[0], int(mid[1:])), t), image_width = '60%')
        classify(pid + '-' + fid, l)
        out += fragment(fid, texts[i], notes = apparatus('{:03d}.{}'.format(p, fid), texts[i], (p, 'main', i + 1)) + finwake((p, 'main', i + 1), texts[i]) + notons((p, 'main', i + 1), texts[i]) + audio((p, i + 1), texts[i]))
    for (comp, mid, t) in [x for (at, xs) in sorted(margins.items()) if at >= len(main) for x in xs]:
        out += fragment(mid, t, notes = apparatus('{:03d}.{}'.format(p, mid), t) + finwake((p, mid[0], int(mid[1:])), t), image_width = '60%')
    ft = balance([dashes(l['t']) for l in page.get('F', [])])
    for (i, l) in enumerate(page.get('F', [])):
        fid = 'F{:02d}'.format(i + 1)
        classify(pid + '-' + fid, dict(l, p = re.match(r'\d+ ', l['t']) is not None), center = False)
        out += fragment(fid, ft[i], notes = apparatus('{:03d}.{}'.format(p, fid), ft[i]) + finwake((p, 'F', i + 1), ft[i]) + notons((p, 'F', i + 1), ft[i]))
    # Links to the images of the page in the scanned editions.
    line = '|Page images: 1939 Faber, 1958 Viking.'
    links = ['/ += . "1939 Faber" -> ' + image(F_ITEM, F[p]['scan']),
             '/ += . "1958 Viking" -> ' + image(V_ITEM, V[p]['scan'])]
    if p in ROSE_PAGES:
        r = ROSE_PAGES[p]
        pp = 'p. {}'.format(r['from']) if r['from'] == r['to'] else 'pp. {}–{}'.format(r['from'], r['to'])
        line += ' Edition of 2010 (Rose and O\'Hanlon): {}, on the James Joyce Digital Archive.'.format(pp)
        links.append('/ += . "{}" -> {}'.format(re.escape(pp), fragment_url(r['jjda'], r['start'])))
    out += [line, '/ id scans'] + links + ['']
    return out

def selectors(anchors):
    return ',\n'.join('a[name="{}"] + p'.format(a) for a in anchors)

def layout():
    """The generated style sheet: deck attributes for layout.conf."""
    css = ['/* The layout of the lines of the pages. Generated by tools/mkdeck.py. */',
           '/* All the lines of a page: justified, never broken. */',
           'a[name^="p"] + p { text-align: justify; text-align-last: justify; min-width: max-content; }',
           '/* Marginalia of II.2. */',
           'a[name^="p"][name*="-L"] + p { float: left; clear: left; width: 24%; margin-left: -36%; min-width: 0;',
           '    text-align: left; text-align-last: auto; font-style: italic; font-size: 65%; line-height: 1.6; }',
           'a[name^="p"][name*="-R"] + p { float: right; clear: right; width: 22%; margin-right: -30%; min-width: 0;',
           '    text-align: left; text-align-last: auto; font-variant: small-caps; font-size: 60%; line-height: 1.8; }',
           '/* Footnotes of II.2. */',
           'a[name^="p"][name*="-F"] + p { font-size: 75%; }',
           'a[name^="p"][name$="-F01"] + p { border-top: 1px solid #888; padding-top: 0.5em; }',
           '/* The links to the page images. */',
           'a[name^="p"][name$="-scans"] + p { text-align-last: auto; min-width: 0; font-size: 75%; margin-top: 1em; color: #666; }',
           '/* No identifiers in the margin of marginalia, headings and the links to the page images. */',
           'p.margin-left:has(+ a[name*="-L"]), p.margin-left:has(+ a[name*="-R"]),',
           'p.margin-left:has(+ p.margin-right + a[name*="-L"]), p.margin-left:has(+ p.margin-right + a[name*="-R"]),',
           'p.margin-left:has(+ a[name$="-chapter"]), p.margin-left:has(+ a[name$="-scans"]) { display: none; }',
           '/* Lines not set to the full measure. */',
           selectors(RAGGED) + ' { text-align-last: auto; }',
           '/* Lines starting a paragraph. */',
           selectors(INDENT) + ' { text-indent: 1.5em; }',
           '/* Centred lines. */',
           selectors(CENTER) + ' { text-align: center; text-align-last: center; }',
           '/* Pages and footnotes set to a narrower measure (II.2). */']
    for ((p, comp), w) in sorted(MEASURE.items()):
        if w < COLUMN - 20:
            sel = 'a[name^="p{:03d}-F"]'.format(p) if comp == 'F' else 'a[name^="p{:03d}-"]:not([name*="-F"])'.format(p)
            css.append('{} + p {{ max-width: {}px; }}'.format(sel, w))
    out = ['/// C The layout of the lines of the pages. Generated by tools/mkdeck.py.']
    for c in css:
        for l in c.split('\n'):
            out.append('/// +html.style ' + l)
    return out

BOOKS = { 'I' : 'Book I', 'II' : 'Book II', 'III' : 'Book III', 'IV' : 'Book IV' }

def contents(pages):
    """The contents card: every page, by chapter, and every series."""
    out = ['// C Generated by tools/mkdeck.py.',
           '// name Contents',
           '// id contents',
           '// +frag.id.show -',
           '// brief All pages of Finnegans Wake by chapter, and the series.',
           '// +html.style p { margin: 0.6em 0; text-align: justify; }',
           'Every page of the book, by book and chapter. A page belongs to the series of',
           'the whole book, of its book and of its chapter; each series can be read',
           'card by card (the arrows at the bottom of each page) or as one long page',
           '("flat").',
           '/ id top', '']
    for (b, title) in BOOKS.items():
        out += ['; head', '/ level 3', '/ id book-' + b, '|' + title, '']
        for (c, start) in CHAPTERS:
            if c.split('.')[0] != b:
                continue
            mine = [p for p in pages if chapter(p) == c]
            label = c if c != b else 'IV'
            out.append('|{}: {}'.format(label, ' '.join(str(p) for p in mine)))
            out.append('/ id ' + c.replace('.', '-'))
            out.append('/ += . "^{}" -> series_{}_compact.html'.format(re.escape(label), c))
            for p in mine:
                out.append('/ += . "(?<=[ ]){}(?![0-9])" -> !p{:03d}'.format(p, p))
            out.append('')
    out += ['; head', '/ level 3', '/ id series', '|Series', '']
    out += ['|The whole book; the books I, II, III, IV; the chapters I.1 to IV.',
            '/ += . "The whole book" -> series_book_compact.html']
    for b in BOOKS:
        out.append('/ += . "(?<=[ ;,]){}(?=[,;])" -> series_{}_compact.html'.format(b, b))
    out += ['']
    return out

def main():
    data = json.load(open(sys.argv[1]))
    outdir = sys.argv[2]
    text = { int(p) : v for (p, v) in data['text'].items() }
    MEASURE.update(measures(text))
    fw = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'finwake.json')
    if os.path.exists(fw):
        for (p, comp, line, lemma, url, token) in json.load(open(fw)):
            FINWAKE[(p, comp, line)].append((dashes(lemma), url, token))
    ro = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rose.json')
    if os.path.exists(ro):
        d = json.load(open(ro))
        for (p, comp, line, tok, whole, old, new, near, url, first) in d['notes']:
            ROSE[(p, comp, line)].append({ 'token' : tok, 'whole' : whole, 'old' : old, 'new' : new,
                                           'near' : near, 'url' : url, 'first' : first })
        ROSE_PAGES.update({ int(p) : v for (p, v) in d['pages'].items() })
    no = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'notons.json')
    if os.path.exists(no):
        for (p, comp, line, tok, lemma, nb, url) in json.load(open(no)):
            NOTONS[(p, comp, line)].append((lemma, nb, url, tok))
    au = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio.json')
    if os.path.exists(au):
        for (p, line, url, reader, part) in json.load(open(au)):
            AUDIO[(p, line)].append((url, reader, part))
    pages = sorted(text)
    F, V = f_pages(), v_pages()
    for (c, start) in CHAPTERS:
        cards = []
        mine = [p for p in pages if chapter(p) == c]
        for p in mine:
            cards.append('\n'.join(card(p, text[p], p == start, F, V)))
        with open(os.path.join(outdir, c + '.deck'), 'w') as fd:
            fd.write('// C Finnegans Wake, chapter {}: pages {}-{}. Generated by tools/mkdeck.py.\n'.format(c, mine[0], mine[-1]))
            fd.write('\n\\\n\n'.join(cards))
            fd.write('\n')
    with open(os.path.join(outdir, 'layout.conf'), 'w') as fd:
        fd.write('\n'.join(layout()) + '\n')
    with open(os.path.join(outdir, 'contents.deck'), 'w') as fd:
        fd.write('\n'.join(contents(pages)) + '\n')

if __name__ == '__main__':
    main()
