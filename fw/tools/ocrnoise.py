"""Classify a difference between two readings as a probable OCR confusion."""
import difflib, unicodedata

CONFUSIONS = set()
for (a, b) in [('u', 'n'), ('m', 'rn'), ('m', 'in'), ('m', 'ni'), ('h', 'b'), ('l', '1'), ('I', 'l'), ('i', 'l'), ('I', '1'),
               ('t', 'f'), ('e', 'c'), ('o', '0'), ('O', '0'), (',', '.'), ('?', '.'), (',', ''), ('.', ''), ('y', ','),
               ('!', 'l'), ('!', 'I'), ('!', '1'), (' ', ''), ("'", ''), ("'", '*'), ("'", '"'), ('"', ''), ('n', 'ri'),
               ('d', 'cl'), ('w', 'vv'), ('li', 'h'), ('ii', 'u'), ('ti', 'd'), ('fi', 'h'), ('tt', 'ti'), ('rn', 'ni'),
               ('c', 'o'), ('a', 'o'), ('s', 'a'), ('f', 'j'), ('(', '{'), (')', '}'), ('(', '|'), ('v', 'y'),
               ('_', ''), ('-', ''), ('S', 's'), ('C', 'c'), ('O', 'o'), ('V', 'v'), ('W', 'w'), ('X', 'x'), ('Z', 'z'),
               ('P', 'p'), ('K', 'k'), ('U', 'u'), ('.', ':'), (',', ';'), (';', ':'), ('!', ''), ('j', 'y'), ('r', 't')]:
    CONFUSIONS.add((a, b))
    CONFUSIONS.add((b, a))

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def ocr_like(correct, read):
    """True if 'read' can be explained as an OCR misreading of 'correct'."""
    a, b = strip_accents(correct), strip_accents(read)
    if a == b:
        return True
    for (tag, i1, i2, j1, j2) in difflib.SequenceMatcher(None, a, b, autojunk = False).get_opcodes():
        if tag == 'equal':
            continue
        x, y = a[i1:i2], b[j1:j2]
        if '?' in y or '^' in y or not y.strip() and not x.strip():
            continue
        if (x, y) in CONFUSIONS:
            continue
        # Several confusions in one chunk.
        if len(x) == len(y) and all(p == q or (p, q) in CONFUSIONS for (p, q) in zip(x, y)):
            continue
        return False
    return True
