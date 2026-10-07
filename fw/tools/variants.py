"""Differences between the editions, as recorded by hand in observed.txt
after comparing the page images of the 1939 (Faber) and 1958 (Viking)
printings (see imgcmp.py, candidates.py, reocr.py and revsheet.py).

Each line of observed.txt is "REF | 1939 reading | 1958 reading", or
"REF | layout | comment" for a passage that the two printings divide into
lines differently. "om." for a reading marks an omission.

The apparatus note on a lemma follows the usual form of a critical
apparatus: "lemma] SIGLA; reading SIGLA", where the sigla are

    1939  Faber and Faber, London, and Viking, New York: the first edition
    1958  Viking, New York (photo-offset, with Joyce's corrections)
"""

import os, re

HERE = os.path.dirname(os.path.abspath(__file__))

def observed():
    out = []
    for line in open(os.path.join(HERE, 'observed.txt'), encoding = 'utf-8'):
        line = line.rstrip('\n')
        if not line.strip() or line.startswith('#'):
            continue
        (ref, a, b) = [x.strip() for x in line.split('|')]
        out.append((ref, a, b))
    return out

VARIANTS = [(r, a, b) for (r, a, b) in observed() if a != 'layout']
LAYOUT = [(r, b) for (r, a, b) in observed() if a == 'layout']

def strip(s):
    return s.replace('_', '')

def notes(ref, text):
    """The apparatus notes of the line ref with the established text: a list
    of (regular expression locating the lemma, note text)."""
    out = []
    t = strip(text)
    for (r, a, b) in VARIANTS:
        if r != ref:
            continue
        if a == 'om.':
            out.append((re.escape(b), '{}] 1958; om. 1939'.format(b)))
        elif b in t and a not in t:
            out.append((re.escape(b), '{}] 1958; {} 1939'.format(b, a)))
        elif a in t and b not in t:
            out.append((re.escape(a), '{}] 1939; {} 1958'.format(a, b)))
        elif b in t:
            out.append((re.escape(b), '{}] 1958; {} 1939'.format(b, a)))
        else:
            raise ValueError('{}: neither "{}" nor "{}" in "{}"'.format(ref, a, b, text))
    for (r, comment) in LAYOUT:
        if r == ref:
            first = t.split()[0]
            text = comment if comment != 'Viking resets the lines' else \
                'the lines from here on are divided differently in 1939 and 1958'
            out.append(('^' + re.escape(first), text))
    return out
