#!/usr/bin/env python3
"""Parse the transcriptions of Finnegans Wake into a common per-page form.

Witnesses:

    W  Oxford Text Archive 1709, David Wilson, Faber 1964 (plain text,
       original line and page breaks, page numbers as "[N]").
    T  Oxford Text Archive 1696, Theall (the "Trent text"), Faber 1950
       (CP437, pages separated by "<*page*>", II.2 margins and footnotes
       labelled "(*L1*)", "(*R1*)", "(*F1*)").

The common form is a dictionary from the page number to a dictionary with keys
"main", "L", "R" and "F", each a list of lines. A line is a dictionary with the
text ("t") and, for the main text, whether the line starts a paragraph ("p").
Italics are marked with "_" in the text. For W, a margin or footnote line also
records the index of the main line next to which it is printed ("at").
"""

import re, sys, json, os

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')

# Pages are numbered 3..628, except for the part title pages.
PAGES = [p for p in range(3, 629) if p not in (217, 218, 400, 401, 402, 591, 592)]
II2 = range(260, 309)

# Wilson's escapes for accented letters.
W_ACCENTS = { '1' : 'é', '2' : 'è', '3' : 'à', '4' : 'î', '6' : 'ô', '7' : 'ê',
              '8' : 'ù', 'E' : 'ù', 'F' : 'ó', 'G' : 'â', '+' : 'ñ' }

W_HEX = { 'EA' : 'à', 'EB' : 'è', 'E1' : 'é', 'EE' : 'ù', 'F5' : 'ç' }

def w_accents(s):
    s = re.sub(r'\\(EA|EB|E1|EE|F5)', lambda m: W_HEX[m.group(1)], s)
    return re.sub(r'&([12346780EFG+])', lambda m: W_ACCENTS[m.group(1)], s)

def italics(s):
    """Both transcriptions mark italics with asterisks, T also with ^A...^B."""
    return s.replace('*', '_').replace('\x01', '_').replace('\x02', '_')

def w_dashes(s):
    """Wilson writes the (spaced) em dash as a single hyphen."""
    return re.sub(r'(^|\s)-(?:\s+|(?=[\w_\'"(.]))', r'\1-- ', s)

def w_pages():
    text = open(os.path.join(SRC, '1709/1709/finnegans1709.txt'), encoding = 'ascii').read()
    pages = {}
    cur = []
    for line in text.split('\n'):
        if re.fullmatch(r'Chapter \d+', line.strip()):
            continue
        m = re.search(r'\s*\[(\d+)\]\s*$', line)
        if m:
            line = line[:m.start()]
            if line.strip() != '' or (cur and cur[-1].strip() != ''):
                cur.append(line)
            pages[int(m.group(1))] = cur
            cur = []
        else:
            cur.append(line)
    assert sorted(pages) == PAGES, set(PAGES) ^ set(pages)
    out = {}
    for p in PAGES:
        lines = [w_dashes(w_accents(italics(l.rstrip()))) for l in pages[p]]
        out[p] = w_ii2(lines) if p in II2 else w_regular(lines)
    return out

def w_regular(lines):
    main = []
    for l in lines:
        if l.strip() == '':
            continue
        main.append({ 't' : l.strip(), 'p' : l.startswith('   ') })
    return { 'main' : main, 'L' : [], 'R' : [], 'F' : [] }

# In II.2 the main text starts at column 22 and the right margin at column 71
# (sometimes a little earlier, when the main line is long).
W_MAIN_COL = 22

def w_ii2(lines):
    main, L, R, F = [], [], [], []
    # Footnotes: after the last blank line block that is followed by lines
    # starting with a footnote number.
    split = len(lines)
    for i in range(len(lines)):
        if re.match(r'\s{1,4}\d+ \S', lines[i]) and \
           all(re.match(r'\s{1,4}\d+ \S|\S', l) or l.strip() == '' for l in lines[i:]) or \
           re.match(r'\s*\d{1,2} [A-Z]', lines[i]) and i > 0 and lines[i - 1].strip() == '':
            split = i
            break
    for l in lines[split:]:
        if l.strip() == '':
            continue
        F.append({ 't' : l.strip(), 'p' : re.match(r'\s{1,4}\d+ ', l) is not None })
    for l in lines[:split]:
        if l.strip() == '':
            continue
        if re.match(r'\s{0,4}\S', l) and len(l.strip()) > 30 and not re.search(r'\S\s{3,}\S', l[:W_MAIN_COL + 2]):
            # A full width line (pp. 287-292): no marginalia.
            main.append({ 't' : l.strip(), 'p' : l.startswith('   ') })
            continue
        left = l[:W_MAIN_COL].strip()
        rest = l[W_MAIN_COL:] if len(l) > W_MAIN_COL else ''
        # Left margin text can run into the main column only if followed by
        # at least two blanks.
        if len(l) > W_MAIN_COL and l[W_MAIN_COL - 1] != ' ' and left != '':
            m = re.match(r'(\S.*?\S)\s{2,}(.*)$', l)
            if m and m.start(2) >= W_MAIN_COL - 2:
                left, rest = m.group(1), l[m.start(2):]
        m = re.match(r'(.*?\S)\s{3,}(\S.*)$', rest)
        right = ''
        if m and m.start(2) >= 40:
            rest, right = m.group(1), m.group(2)
        here = len(main)
        if rest.strip() != '':
            main.append({ 't' : rest.strip(), 'p' : rest.startswith('   ') })
        if left != '':
            L.append({ 't' : left, 'at' : here })
        if right != '':
            R.append({ 't' : right, 'at' : here })
    return { 'main' : main, 'L' : L, 'R' : R, 'F' : F }

def t_pages():
    raw = open(os.path.join(SRC, '1696/1696/finnegans1696.txt'), 'rb').read().decode('cp437')
    raw = raw.replace('/*Part*/', '').replace('{*Episode*}', '')
    chunks = raw.split('<*page*>')
    assert chunks[0].strip() == ''
    chunks = chunks[1:]
    assert len(chunks) == len(PAGES), len(chunks)
    out = {}
    for (p, chunk) in zip(PAGES, chunks):
        out[p] = t_page(chunk.split('\n'), p in II2)
    return out

T_LABEL = re.compile(r'^\s*\(\*([LRF])(\d+)\*\)')

def t_page(lines, ii2):
    main, parts = [], { 'L' : [], 'R' : [], 'F' : [] }
    last = None
    for l in lines:
        l = l.rstrip()
        if l.strip() == '':
            last = None if not ii2 else last
            continue
        m = T_LABEL.match(l) if ii2 else None
        if m:
            text = italics(l[m.end():].strip())
            last = { 't' : text, 'n' : int(m.group(2)) }
            parts[m.group(1)].append(last)
            last['k'] = m.group(1)
        elif ii2 and last is not None and last['k'] == 'F':
            # A footnote line wrapped by the transcriber.
            last['t'] = (last['t'] + ' ' + italics(l.strip())).strip()
        else:
            last = None
            main.append({ 't' : italics(l.strip()), 'p' : l.startswith('  ') })
    for k in parts:
        for x in parts[k]:
            del x['k']
    if ii2:
        # Footnote references: "thunder. 3" for "thunder.3".
        for l in main + parts['L'] + parts['R']:
            l['t'] = re.sub(r'([^\s\d]) (\d{1,2})(?=\s|$|[)])', r'\1\2', l['t'])
    if ii2 and not parts['F']:
        # Unlabelled footnotes (287-292): the numbered lines at the end.
        fn = None
        for (i, l) in enumerate(main):
            if re.match(r'\d+ [A-Z(]', l['t']) and l['p'] and all(re.match(r'\d+ ', x['t']) or not x['p'] for x in main[i:]):
                fn = i
                break
        if fn is not None:
            for l in main[fn:]:
                if l['p']:
                    parts['F'].append({ 't' : l['t'], 'p' : True })
                else:
                    parts['F'][-1]['t'] += ' ' + l['t']
            main = main[:fn]
    return { 'main' : main, **parts }

if __name__ == '__main__':
    w = w_pages()
    t = t_pages()
    json.dump({ 'W' : w, 'T' : t }, open(sys.argv[1] if len(sys.argv) > 1 else '/dev/stdout', 'w'),
              ensure_ascii = False, indent = None)
