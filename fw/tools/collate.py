#!/usr/bin/env python3
"""Collate the witnesses of Finnegans Wake and establish the text.

The established text is the corrected Faber/Viking text (the text of the
printings that include Joyce's own "Corrections of Misprints"), divided into
pages and lines as in the Faber and Viking printings and numbered by Fweet's
rules (see fweet_rules.py).

Witnesses (see witnesses.py and scans.py):

    W  Wilson, Faber 1964, transcription
    T  Theall, Faber 1950, transcription
    V  Viking 1958, OCR
    F  Faber 1939, OCR

A page consists of components: "main" (the main text) and, in II.2, "L" and
"R" (left and right marginalia) and "F" (footnotes). The lines of a component
are taken from W, or from T where W lacks them. The physical lines of the
scans (V, or F) decide which lines exist.

The words are established by voting. W is the base: its tokens are aligned
with the tokens of each other witness. Where W and T agree, their reading is
accepted. Where they disagree, the reading supported by V (or, failing that,
by F) wins. Unresolved disagreements keep the W reading and are reported.
Finally, corrections from overrides.py, checked against the scans by hand,
are applied.

Every decision is recorded. The output is a JSON file with the text (for
every page, the lines of each component, each line a dictionary with the text
"t", paragraph start "p" and the collation records "c") and the log of all
records.
"""

import re, sys, json, difflib, collections
from witnesses import w_pages, t_pages, PAGES, II2
from scans import f_pages, v_pages, ii2_split
from fweet_rules import expected, VERSES
import overrides

COMPONENTS = ('main', 'L', 'R', 'F')

def typo(s):
    """Typographic normalisation applied to all witnesses."""
    s = s.replace('’', "'").replace('‘', "'").replace('`', "'")
    s = s.replace('“', '"').replace('”', '"').replace('„', '"')
    s = s.replace('—', '--').replace('–', '--')
    s = re.sub(r'\s+([!?;:])', r'\1', s)       # French spacing of the 1939 setting.
    s = re.sub(r'\s*--\s*', ' -- ', s)          # Spaced em dash.
    s = re.sub(r'\.\s?\.\s?\.', '. . .', s)      # Spaced ellipsis.
    return s.strip()

def ocr(s):
    """OCR artifacts."""
    return s.replace('.^', '?').replace('^', '?').replace('®', '?')

def key(tok):
    """Comparison key of a token."""
    return tok.replace('_', '')

def tokens(lines):
    """Tokens of a list of lines and the line index of each token."""
    toks, where = [], []
    for (i, l) in enumerate(lines):
        for t in l.split():
            toks.append(t)
            where.append(i)
    return toks, where

def align(a, b):
    sm = difflib.SequenceMatcher(None, [key(x) for x in a], [key(x) for x in b], autojunk = False)
    return sm.get_opcodes()

def project(ops, i1, i2):
    """The region of b corresponding to the region [i1, i2) of a."""
    j1 = j2 = None
    for (tag, a1, a2, b1, b2) in ops:
        if j1 is None and (a1 <= i1 < a2 or a1 == a2 == i1):
            j1 = b1 + (i1 - a1 if tag == 'equal' else 0)
        if a1 < i2 <= a2 or (a1 == a2 == i2 and j2 is None and j1 is not None):
            j2 = b1 + (i2 - a1) if tag == 'equal' else b2
            if a1 < i2 <= a2:
                break
    if j1 is None:
        j1 = ops[-1][4] if ops else 0
    if j2 is None:
        j2 = j1
    return j1, max(j1, j2)

def similarity(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk = False).ratio()

def vote(w, t, v, f):
    """Choose between the W and T readings of a region, given the
    corresponding regions of the scans. Returns (reading, who)."""
    if not t:
        return (w, 'W')  # Deletions are decided by the caller.
    ws, ts = ' '.join(key(x) for x in w), ' '.join(key(x) for x in t)
    vs, fs = ' '.join(key(x) for x in v), ' '.join(key(x) for x in f)
    for s in (vs, fs):
        if s == ts and s != ws:
            return (t, 'T')
        if s == ws and s != ts:
            return (w, 'W')
    if ws.replace('_', '') == ts.replace('_', ''):
        return (w, 'W') # Italics: only the transcriptions have them; prefer W.
    if len(w) == len(t) and len(w) > 1:
        # Vote token by token.
        sv, sf = set(key(x) for x in v), set(key(x) for x in f)
        out, whos = [], set()
        for (a, b) in zip(w, t):
            if key(a) == key(b):
                out.append(a)
            else:
                (r, who) = vote([a], [b], [x for x in v if x in sv], [x for x in f if x in sf])
                out.append(r[0] if r else a)
                whos.add(who)
        if '?' not in whos:
            return (out, 'WT')
    score_w = similarity(ws, vs) + similarity(ws, fs)
    score_t = similarity(ts, vs) + similarity(ts, fs)
    if abs(score_w - score_t) >= 0.1:
        return (w, 'W~') if score_w > score_t else (t, 'T~')
    return (w, '?')

def line_align(ref, other, band = 6):
    """Monotonic alignment of two lists of lines by similarity. Returns a
    dictionary from the indices of ref to the indices of other."""
    n, m = len(ref), len(other)
    R = [key(typo(x)).lower() for x in ref]
    O = [key(typo(x)).lower() for x in other]
    sim = {}
    def s(i, j):
        if (i, j) not in sim:
            r = similarity(R[i], O[j])
            sim[(i, j)] = r - 0.5 if r > 0.5 else -1
        return sim[(i, j)]
    NEG = -10**9
    best = [[NEG] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]
    best[0][0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            if best[i][j] == NEG:
                continue
            for (di, dj) in ((1, 0), (0, 1), (1, 1)):
                a, b = i + di, j + dj
                if a > n or b > m:
                    continue
                gain = 0
                if di and dj:
                    if abs(a - b) > band + abs(n - m):
                        continue
                    gain = s(i, j)
                    if gain < 0:
                        continue
                if best[i][j] + gain > best[a][b]:
                    best[a][b] = best[i][j] + gain
                    back[a][b] = (i, j)
    out = {}
    (i, j) = (n, m)
    while (i, j) != (0, 0):
        (pi, pj) = back[i][j]
        if i - pi == 1 and j - pj == 1:
            out[pi] = pj
        (i, j) = (pi, pj)
    return out

def fill_gaps(a, n, m):
    """Pair the unaligned lines between two aligned ones in order, when there
    are as many on both sides."""
    anchors = [(-1, -1)] + sorted(a.items()) + [(n, m)]
    out = dict(a)
    for ((i0, j0), (i1, j1)) in zip(anchors, anchors[1:]):
        if i1 - i0 == j1 - j0 and i1 - i0 > 1:
            for k in range(1, i1 - i0):
                out[i0 + k] = j0 + k
    return out

def structure(p, comp, Wl, Tl, Vl, Fl, e, log):
    """The lines of a component: the physical lines of a scan, each filled
    with the corresponding line of W, or of T where W lacks it.

    Returns (lines, ref): ref is the list of the reference scan lines if the
    page has to be re-broken at them (the lines are reflowed in the reference
    scan), None otherwise."""
    if e is None:
        votes = collections.Counter([len(Vl), len(Fl), len(Wl), len(Tl)])
        e = max(votes, key = lambda n: (votes[n], n == len(Wl), n == len(Vl)))
    if len(Vl) == e:
        ref, refname = Vl, 'V'
    elif len(Fl) == e:
        ref, refname = Fl, 'F'
    elif len(Wl) == e:
        return Wl, None
    elif len(Tl) == e:
        return [dict(l, src = 'T') for l in Tl], None
    else:
        ref, refname = Vl, 'V'
    rt = [l['t'] for l in ref]
    aw = fill_gaps(line_align(rt, [l['t'] for l in Wl]), len(rt), len(Wl))
    at = fill_gaps(line_align(rt, [l['t'] for l in Tl]), len(rt), len(Tl))
    out = []
    reflow = False
    for i in range(len(rt)):
        if i in aw:
            out.append(Wl[aw[i]])
        elif i in at:
            out.append(dict(Tl[at[i]], src = 'T'))
            log.append({ 'kind' : 'line', 'page' : p, 'comp' : comp, 'line' : i + 1, 'src' : 'T', 't' : Tl[at[i]]['t'] })
        else:
            reflow = True
    if reflow:
        log.append({ 'kind' : 'layout', 'page' : p, 'comp' : comp, 'line' : 0, 'ref' : refname,
                     'W' : [l['t'] for l in Wl], refname : rt })
        # Keep all the lines of W in order; the page is re-broken at the
        # lines of the reference scan.
        return list(Wl), ref
    return out, None

def italics_of(w, choice):
    """Carry the italics of the W reading over to the chosen reading: only W
    marks italics reliably. W's markers at the start of its first token and
    at the end of its last are put at the corresponding places of the
    choice."""
    if not w or not choice:
        return choice
    choice = list(choice)
    m = re.match(r'^((?:[^\w]|_)*)', w[0]).group(1)
    if '_' in m and not re.match(r'^[^\w]*_', choice[0]):
        lead = re.match(r'^([^\w]*)', choice[0]).group(1)
        choice[0] = lead + '_' + choice[0][len(lead):]
    m = re.search(r'((?:[^\w]|_)*)$', w[-1]).group(1)
    if '_' in m and not re.search(r'_[^\w]*$', choice[-1]):
        # Put the marker after the last letter and after as many characters
        # of the punctuation that follows it as W has inside the italics.
        inside = len(m[:m.rindex('_')])
        trail = re.search(r'([^\w]*)$', choice[-1]).group(1)
        k = len(choice[-1]) - len(trail) + min(inside, len(trail))
        choice[-1] = choice[-1][:k] + '_' + choice[-1][k:]
    return choice

def establish(p, comp, wl, tl, vl, fl, ref, log, base_is_w = True):
    """Establish the text of one component of a page.

    wl: base lines (dicts with 't' and 'p'), tl, vl, fl: lists of strings,
    ref: the reference scan lines to re-break at (or None).
    Returns the list of established lines.
    """
    wt, wwhere = tokens([typo(l['t']) for l in wl])
    tt, _ = tokens([typo(l) for l in tl])
    vt, _ = tokens([ocr(typo(l)) for l in vl])
    ft, _ = tokens([ocr(typo(l)) for l in fl])
    if not wt:
        return []
    ops_t = align(wt, tt)
    ops_v = align(wt, vt)
    ops_f = align(wt, ft)
    out = list(wt) # Established tokens, parallel to wt.
    recs = collections.defaultdict(list)
    def region(ops, toks, i1, i2):
        (j1, j2) = project(ops, i1, i2)
        return toks[j1:j2]
    def same(x, y):
        return [key(t) for t in x] == [key(t) for t in y]
    def note(i1, rec):
        i = min(i1, len(wt) - 1)
        recs[i].append(rec)
        log.append(dict(rec, page = p, comp = comp, line = wwhere[i] + 1))
    for (tag, i1, i2, j1, j2) in ops_t:
        if tag == 'equal':
            continue
        w = wt[i1:i2]
        t = tt[j1:j2]
        v = region(ops_v, vt, i1, i2)
        f = region(ops_f, ft, i1, i2)
        if not t and base_is_w:
            # T lacks words that W has: keep them if a scan has them nearby.
            (j1v, j2v) = project(ops_v, i1, i2)
            (j1f, j2f) = project(ops_f, i1, i2)
            near = set(key(x).lower() for x in vt[max(0, j1v - 6):j2v + 6] + ft[max(0, j1f - 6):j2f + 6])
            found = sum(1 for x in w if key(x).lower() in near or
                        any(similarity(key(x).lower(), y) > 0.75 for y in near))
            (choice, who) = (w, 'W') if found >= max(1, len(w) / 2) else (t, 'T-')
        else:
            (choice, who) = vote(w, t, v, f)
        note(i1, { 'kind' : 'WT', 'who' : who, 'W' : ' '.join(w), 'T' : ' '.join(t),
                   'V' : ' '.join(v), 'F' : ' '.join(f) })
        if choice is not w:
            choice = italics_of(w, choice)
            if i2 - i1 == len(choice):
                for k in range(len(choice)):
                    out[i1 + k] = choice[k]
            elif i2 > i1:
                out[i1] = ' '.join(choice)
                for k in range(i1 + 1, i2):
                    out[k] = ''
            elif i1 > 0:      # Insertion: attach to the previous token.
                out[i1 - 1] = (out[i1 - 1] + ' ' + ' '.join(choice)).strip()
            else:
                out[0] = (' '.join(choice) + ' ' + out[0]).strip()
    # Where W and T agree but both scans disagree with them in the same way.
    for (tag, i1, i2, j1, j2) in ops_v:
        if tag == 'equal':
            continue
        v = vt[j1:j2]
        f = region(ops_f, ft, i1, i2)
        t = region(ops_t, tt, i1, i2)
        w = wt[i1:i2]
        if same(w, t) and same(v, f) and not same(v, w):
            note(i1, { 'kind' : 'scans', 'W' : ' '.join(w), 'T' : ' '.join(t), 'V' : ' '.join(v), 'F' : ' '.join(f) })
    # Lines of the established text.
    if ref is None:
        lines = [[] for _ in wl]
        lrecs = [[] for _ in wl]
        for (i, tok) in enumerate(out):
            if tok != '':
                lines[wwhere[i]].append(tok)
            lrecs[wwhere[i]] += recs.get(i, [])
        paras = [l.get('p', False) for l in wl]
    else:
        (lines, lrecs, paras) = rebreak(out, wwhere, recs, wl, ref)
    return [{ 't' : ' '.join(lines[i]), 'p' : paras[i], 'c' : lrecs[i] } for i in range(len(lines))]

def rebreak(out, wwhere, recs, wl, ref):
    """Divide the established tokens into the lines of the reference scan."""
    toks = []   # (token, index in out)
    for (i, tok) in enumerate(out):
        for x in tok.split():
            toks.append((x, i))
    rt, rwhere = tokens([ocr(typo(l['t'])) for l in ref])
    ops = align([x for (x, _) in toks], rt)
    # For every reference line, the established token where it starts.
    starts = []
    for k in range(len(ref)):
        j = rwhere.index(k) if k in rwhere else None
        i = None
        if j is not None:
            for (tag, a1, a2, b1, b2) in ops:
                if b1 <= j < b2:
                    i = a1 + (j - b1 if tag == 'equal' else 0)
                    break
        starts.append(i)
    # Monotonic, and fill unknown starts.
    last = 0
    for k in range(len(starts)):
        if starts[k] is None or starts[k] < last:
            starts[k] = last
        last = starts[k]
    starts.append(len(toks))
    lines, lrecs, paras = [], [], []
    for k in range(len(ref)):
        seg = toks[starts[k]:starts[k + 1]]
        lines.append([x for (x, _) in seg])
        idx = sorted(set(i for (_, i) in seg))
        lrecs.append(sum([recs.get(i, []) for i in idx], []))
        first = seg[0][1] if seg else None
        paras.append(first is not None and wl[wwhere[first]].get('p', False) and
                     (first == 0 or wwhere[first - 1] != wwhere[first]))
    return lines, lrecs, paras

def first_edition(p, comp, est, fl, log):
    """Record the differences between the established text and the first
    edition (Faber 1939, OCR)."""
    et, ewhere = tokens([l['t'] for l in est])
    ft, _ = tokens([ocr(typo(l)) for l in fl])
    if not et:
        return
    for (tag, i1, i2, j1, j2) in align(et, ft):
        if tag == 'equal':
            continue
        line = ewhere[min(i1, len(ewhere) - 1)]
        rec = { 'kind' : '1939', 'C' : ' '.join(et[i1:i2]), 'F' : ' '.join(ft[j1:j2]) }
        est[line]['c'].append(rec)
        log.append(dict(rec, page = p, comp = comp, line = line + 1))

def contains(a, b):
    """The lines of b are (approximately) a subsequence of the lines of a."""
    al = line_align([l['t'] for l in b], [l['t'] for l in a])
    return len(al) == len(b)

def ocr_components(p, S, Wp, Tp):
    """The OCR lines of each component of page p of scan S. A line belongs to
    the component of the transcribed line it is most similar to; lines not
    similar to any are classified by their position on the page."""
    if p not in II2:
        return { 'main' : S['lines'], 'L' : [], 'R' : [], 'F' : [] }
    geo = ii2_split(S)
    where = {}
    for k in COMPONENTS:
        for l in geo[k]:
            where[id(l)] = k
    known = [(k, key(typo(l['t'])).lower()) for X in (Wp, Tp) for k in COMPONENTS for l in X[k]]
    out = { k : [] for k in COMPONENTS }
    for l in S['lines']:
        t = key(ocr(typo(l['t']))).lower()
        best, kbest = 0, None
        for (k, x) in known:
            r = difflib.SequenceMatcher(None, t, x, autojunk = False).quick_ratio()
            if r > best:
                r = similarity(t, x)
                if r > best:
                    best, kbest = r, k
        out[kbest if best > 0.6 else where[id(l)]].append(l)
    for k in COMPONENTS:
        out[k].sort(key = lambda l: (l['b'][1], l['b'][0]))
    return out

def run():
    W, T, V, F = w_pages(), t_pages(), v_pages(), f_pages()
    log = []
    text = {}
    for p in PAGES:
        Vc = ocr_components(p, V[p], W[p], T[p])
        Fc = ocr_components(p, F[p], W[p], T[p])
        text[p] = {}
        for comp in COMPONENTS:
            Wl, Tl, Vl, Fl = W[p][comp], T[p][comp], Vc[comp], Fc[comp]
            if not (Wl or Tl):
                text[p][comp] = []
                continue
            if comp == 'main':
                (base, ref) = structure(p, comp, Wl, Tl, Vl, Fl, expected(p), log)
                other = Tl
            else:
                # Marginalia and footnotes: the transcription whose number of
                # lines is confirmed by a scan, W if both or neither are.
                counts = (len(Vl), len(Fl))
                if contains(Tl, Wl) and len(Tl) > len(Wl):
                    (base, other) = ([dict(l, src = 'T') for l in Tl], Wl)
                    log.append({ 'kind' : 'line', 'page' : p, 'comp' : comp, 'line' : 0, 'src' : 'T',
                                 't' : '{} lines from T, {} in W'.format(len(Tl), len(Wl)) })
                elif contains(Wl, Tl) or len(Wl) in counts or len(Tl) not in counts:
                    (base, other) = (Wl, Tl)
                else:
                    (base, other) = ([dict(l, src = 'T') for l in Tl], Wl)
                    log.append({ 'kind' : 'line', 'page' : p, 'comp' : comp, 'line' : 0, 'src' : 'T',
                                 't' : '{} lines from T, {} in W'.format(len(Tl), len(Wl)) })
                ref = None
            est = establish(p, comp, base, [l['t'] for l in other], [l['t'] for l in Vl], [l['t'] for l in Fl], ref, log,
                            base_is_w = other is Tl)
            first_edition(p, comp, est, [l['t'] for l in Fl], log)
            text[p][comp] = est
    scan_breaks(text, F, V, log)
    overrides.apply(text, log)
    layout(text, F, V, W, T)
    overrides.center(text)
    justification(text, F, V, W, T)
    return text, log

def last_words(lines):
    out = []
    for l in lines:
        w = [re.sub(r'[^a-z]', '', key(ocr(typo(x))).lower()) for x in l.split()]
        w = [x for x in w if len(x) > 1]
        out.append(w[-1] if w else '')
    return out

def scan_breaks(text, F, V, log):
    """Where both scans divide a passage into lines in the same way and the
    established text differs from them, re-break the passage at their lines
    (the transcriptions sometimes move a word across a line break)."""
    def same(a, b):
        return a == b or similarity(a, b) >= 0.6
    for p in PAGES:
        if p in II2:
            continue
        est = text[p]['main']
        n = len(est)
        if len(F[p]['lines']) != n or len(V[p]['lines']) != n:
            continue
        ef = last_words([l['t'] for l in est])
        ff = last_words([l['t'] for l in F[p]['lines']])
        vf = last_words([l['t'] for l in V[p]['lines']])
        agree = [same(f, v) for (f, v) in zip(ff, vf)]
        wrong = [i for i in range(n) if agree[i] and not same(ef[i], ff[i])]
        if not wrong:
            continue
        toks = [(x, i) for (i, l) in enumerate(est) for x in l['t'].split()]
        vt, vwhere = tokens([ocr(typo(l['t'])) for l in V[p]['lines']])
        ops = align([x for (x, _) in toks], vt)
        starts = []
        for k in range(n):
            j = vwhere.index(k) if k in vwhere else None
            s = None
            for (tag, a1, a2, b1, b2) in ops:
                if j is not None and b1 <= j < b2:
                    s = a1 + (j - b1 if tag == 'equal' else 0)
                    break
            starts.append(s)
        starts.append(len(toks))
        new = list(est)
        # Blocks of consecutive wrong lines; the lines from the one before the
        # block to the one after it are re-broken.
        blocks = []
        for i in wrong:
            if blocks and i == blocks[-1][1] + 1:
                blocks[-1][1] = i
            else:
                blocks.append([i, i])
        for (a, b) in blocks:
            lo, hi = max(0, a - 1), min(n - 1, b + 1)
            if not all(agree[k] for k in range(lo, hi + 1)):
                continue
            s = [0 if k == 0 else starts[k] for k in range(lo, hi + 2)]
            if None in s or s != sorted(s):
                continue
            for (k, (x, y)) in zip(range(lo, hi + 1), zip(s, s[1:])):
                seg = toks[x:y]
                t = ' '.join(w for (w, _) in seg)
                if t != est[k]['t']:
                    log.append({ 'kind' : 'break', 'page' : p, 'comp' : 'main', 'line' : k + 1,
                                 'was' : est[k]['t'], 'now' : t })
                    new[k] = dict(est[k], t = t)
        text[p]['main'] = new

def layout(text, F, V, W, T):
    """Record the layout facts the deck needs: for marginalia, the index of
    the main line next to which each is printed ("at"); centred lines
    ("center"); for verses, whether a line is a hanging-indent continuation
    of the previous one ("cont")."""
    for p in II2:
        main = text[p]['main']
        for comp in ('L', 'R'):
            lines = text[p][comp]
            if not lines:
                continue
            for S in (F, V):
                c = ocr_components(p, S[p], W[p], T[p])
                am = line_align([l['t'] for l in main], [l['t'] for l in c['main']])
                ac = line_align([l['t'] for l in lines], [l['t'] for l in c[comp]])
                if len(am) > len(main) // 2 and len(ac) >= len(lines) // 2:
                    break
            ys = { i : c['main'][j]['b'][1] for (i, j) in am.items() }
            last = 0
            for (i, l) in enumerate(lines):
                if i in ac and ys:
                    y = c[comp][ac[i]]['b'][1]
                    at = min(ys, key = lambda k: abs(ys[k] - y))
                else:
                    at = last + (1 if i > 0 else 0)
                l['at'] = max(at, last)
                last = l['at']
    for p in PAGES:
        # Centred lines: from the geometry of the 1939 scan, where its lines
        # correspond one to one to the established ones.
        main, lines = text[p]['main'], F[p]['lines']
        if p in II2 or len(main) != len(lines):
            continue
        xs = sorted(l['b'][0] for l in lines)
        x1s = sorted(l['b'][2] for l in lines)
        left, right = xs[len(xs) // 4], x1s[3 * len(x1s) // 4]
        mid = (left + right) / 2
        for (l, o) in zip(main, lines):
            (a, _, b, _) = o['b']
            if a - left > 0.12 * (right - left) and abs((a + b) / 2 - mid) < 0.04 * (right - left):
                l['center'] = True
    for p in VERSES:
        for (l, o) in zip(text[p]['main'], F[p]['lines']):
            # On pp. 45-46 a continuation starts with "["; elsewhere it is set
            # with a hanging indent (the chorus lines of 45-46 are indented too).
            l['cont'] = l['t'].startswith('[') if p in (45, 46) else 540 <= o['b'][0] < 700

def justification(text, F, V, W, T):
    """Mark the lines that are set to the full measure ("full"): in the scan,
    their right edge is at the right edge of the text block. Such lines are
    justified in the deck; the others (ends of paragraphs, short verse lines)
    are not. Also record the measure of each component of a page relative
    to the measure of the regular pages ("measure")."""
    def block(c):
        rights = sorted(o['b'][2] for o in c)
        lefts = sorted(o['b'][0] for o in c)
        return lefts[len(lefts) // 4], rights[(9 * len(rights)) // 10]
    std = {}
    for (name, S) in (('F', F), ('V', V)):
        ms = []
        for p in PAGES:
            if p not in II2 and expected(p) and len(S[p]['lines']) > 20:
                (l, r) = block(S[p]['lines'])
                ms.append(r - l)
        std[name] = sorted(ms)[len(ms) // 2]
    for p in PAGES:
        for comp in ('main', 'F'):
            lines = text[p].get(comp, [])
            if not lines:
                continue
            for (name, S) in (('F', F), ('V', V)):
                c = ocr_components(p, S[p], W[p], T[p])[comp]
                if not c:
                    continue
                a = line_align([l['t'] for l in lines], [l['t'] for l in c])
                if len(a) < 0.8 * len(lines):
                    continue
                (left, right) = block(c)
                measure = right - left
                text[p].setdefault('measure', {})[comp] = round(measure / std[name], 3)
                for (i, l) in enumerate(lines):
                    if i in a:
                        l['full'] = c[a[i]]['b'][2] >= right - 0.03 * measure
                    elif i > 0 and i - 1 in a:
                        l['full'] = lines[i - 1].get('full', False)
                break

if __name__ == '__main__':
    text, log = run()
    json.dump({ 'text' : text, 'log' : log }, open(sys.argv[1], 'w'), ensure_ascii = False, indent = 0)
    c = collections.Counter((r['kind'], r.get('who', '')) for r in log)
    print(sorted(c.items()))
