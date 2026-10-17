#!/usr/bin/env python3
"""The reader's own notes in the generated decks: the notes that start with
the letter lambda,

    / +* "REGEX" Λ TEXT
    : ...

(the note line and the ":" lines after it). They belong to the fragment (the
printed line) they are in, which the card identifier and the fragment
identifier name ("p003", "23"). When mkdeck.py regenerates a deck, it takes
them from the old deck and puts them back in the new one, after the notes
generated for the same line, in their order.

Nothing else in a generated deck may be edited by hand: it would be lost.
mkdeck.py records a digest of every card it generates (generated.json); a
card whose text without the own notes does not match its digest has been
edited, and mkdeck.py refuses to overwrite it (unless forced).

    personal.py check DECK...    report the cards edited outside own notes
    personal.py list DECK...     list the own notes
"""

import sys, os, re, json, hashlib, collections

LETTER = 'Λ'
NOTE = re.compile(r'^/\s*\+\*\s+"(?:[^"\\]|\\.)*"\s+' + LETTER + r'(\s|$)')
HERE = os.path.dirname(os.path.abspath(__file__))
DIGESTS = os.path.join(HERE, 'generated.json')

def cards(lines):
    """The cards of a deck: [(card identifier, [lines])]. Cards are separated
    by lines "\\"; the separators go with the card they end."""
    out, cur, cid = [], [], None
    for l in lines:
        cur.append(l)
        m = re.match(r'^//\s+id\s+(\S+)', l)
        if m and cid is None:
            cid = m.group(1)
        if l.strip() == '\\':
            out.append((cid, cur))
            cur, cid = [], None
    if cur:
        out.append((cid, cur))
    return out

def split(lines):
    """The lines of a card without its own notes, and the own notes:
    [(fragment identifier, [lines of the note])]."""
    rest, notes = [], []
    here, fid = [], None    # The notes and the identifier of the current fragment.
    note = None
    for l in lines:
        if note is not None and l.startswith(':'):
            note.append(l)
            continue
        note = None
        if not l.strip():
            here, fid = [], None
        m = re.match(r'^/\s+id\s+(\S+)', l)
        if m:
            # The identifier may come after the note, too.
            fid = m.group(1)
            for n in here:
                n[0] = fid
        if NOTE.match(l):
            note = [l]
            here.append([fid, note])
            notes.append(here[-1])
            continue
        rest.append(l)
    return rest, [tuple(n) for n in notes]

def digest(lines):
    """The digest of the lines of a card: blank lines (any number of them, as
    long as there is one) and trailing blanks do not count."""
    text = re.sub(r'\n\s*\n(\s*\n)*', '\n\n', ''.join(l.rstrip() + '\n' for l in lines))
    return hashlib.sha1(text.encode('utf-8')).hexdigest()

def attach(lines, notes):
    """Put the own notes back into the lines of a card: each at the end of
    its fragment. Returns the lines and the notes whose fragment is gone."""
    lines = list(lines)
    lost = []
    for (frag, note) in notes:
        cur, end = None, None
        for (i, l) in enumerate(lines):
            if not l.strip() or l.strip() == '\\':
                if cur == frag and frag is not None:
                    end = i
                    break
                cur = None
            m = re.match(r'^/\s+id\s+(\S+)', l)
            if m:
                cur = m.group(1)
        else:
            if cur == frag and frag is not None:
                end = len(lines)
        if end is None:
            lost.append((frag, note))
        else:
            lines[end:end] = note
    return lines, lost

def read(path):
    if not os.path.exists(path):
        return []
    return open(path, encoding = 'utf-8').read().splitlines(keepends = True)

def digests():
    return json.load(open(DIGESTS)) if os.path.exists(DIGESTS) else {}

def edited(deck, lines, known):
    """The cards of a deck edited outside own notes."""
    name = os.path.basename(deck)
    out = []
    for (cid, cl) in cards(lines):
        d = known.get(name, {}).get(cid)
        if d is not None and digest(split(cl)[0]) != d:
            out.append(cid)
    return out

def regenerate(deck, new, known, force = False):
    """The new text of a deck: the generated text (new, a string) with the
    own notes of the old deck. Records the digests of the new cards in known.
    Raises an error if the old deck was edited outside own notes."""
    old = read(deck)
    bad = edited(deck, old, known)
    if bad and not force:
        raise SystemExit('{}: edited outside own notes ({} notes), not regenerated: {}'.format(
            deck, LETTER, ' '.join(bad)))
    mine = collections.defaultdict(list)
    for (cid, cl) in cards(old):
        mine[cid] += split(cl)[1]
    name = os.path.basename(deck)
    known[name] = {}
    out, count = [], 0
    for (cid, cl) in cards(new.splitlines(keepends = True)):
        known[name][cid] = digest(cl)
        (cl, lost) = attach(cl, mine.pop(cid, []))
        for (frag, note) in lost:
            print('{}: {} {}: line gone, note dropped: {}'.format(deck, cid, frag, note[0].rstrip()), file = sys.stderr)
        count += sum(1 for l in cl if NOTE.match(l))
        out += cl
    for (cid, notes) in mine.items():
        for (frag, note) in notes:
            print('{}: {}: card gone, note dropped: {}'.format(deck, cid, note[0].rstrip()), file = sys.stderr)
    return ''.join(out), count

def save(known):
    with open(DIGESTS, 'w') as fd:
        json.dump(known, fd, indent = 0, sort_keys = True)
        fd.write('\n')

if __name__ == '__main__':
    (cmd, decks) = (sys.argv[1], sys.argv[2:])
    known = digests()
    status = 0
    for deck in decks:
        lines = read(deck)
        if cmd == 'check':
            bad = edited(deck, lines, known)
            if bad:
                print('{}: edited outside own notes: {}'.format(deck, ' '.join(bad)))
                status = 1
        elif cmd == 'list':
            for (cid, cl) in cards(lines):
                for (frag, note) in split(cl)[1]:
                    print('{} {} {}'.format(cid, frag, ''.join(note).rstrip().replace('\n', '\n    ')))
    sys.exit(status)
