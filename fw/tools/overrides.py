"""Corrections to the collated text, each checked by hand against the page
images of the 1939 (Faber) and 1958 (Viking) scans.

LINES maps a line reference to its text: "PPP.LL" for the main text,
"PPP.FLL", "PPP.LLL", "PPP.RLL" for the footnotes and marginalia of II.2.
The text uses "_" for italics.

SUBST lists substitutions (line reference, old, new) applied to the
established lines: the usual way to fix a reading.
"""

SUBST = [
    # Checked against the 1939 and 1958 scans; W and T disagreed.
    ('014.11', '1132', '1132'),
    ('058.26', '(_pardonnez-leur je', '(_pardonnez-leur, je'),
    ('072.09', 'He -- -', 'He -- --'),
    ('075.22', 'missuses) might, mercy', 'missusses) might, mercy'),
    ('088.14', "O'Somebody?", "O' Somebody?"),
    ('094.21', 'A . . .. . .. . ..!', 'A . . . . . . . . . !'),
    ('094.22', '? . . .. . .. . .O!', '? . . . . . . . . . O!'),
    ('105.20', 'COrpse,', 'Corpse,'),
    ('107.34', 'oxhousehumper.)', 'oxhousehumper!)'),
    ('109.06', 'dynadescendanced', 'dynasdescendanced'),
    ('113.09', 'forrader.', 'forrarder.'),
    ('124.08', 'out -> that', 'out → that'),
    ('124.09', 'ad bin', 'ad bîn'),
    ('124.10', 'table;;acùtely', 'table; ; acùtely'),
    ('124.10', '_piquèd_, to=intro', '_piquéd_, to=intro'),
    ('124.11', "sù ' ' fàç'e']", "sù ' ' fàç'e']"),
    ('124.34', 'Pere Adam', 'Père Adam'),
    ('138.36', 'but girdsgirder', 'but girds girder'),
    ('140.27', 'speech. c)', 'speech. _c_)'),
    ('146.10', "th'adult'rous", "th'adult' rous"),
    ('159.17', '_Why, why, why! Weh, O weh', '_Why, why, why! Weh, O weh!'),
    ('183.28', "mothes',", "mothers',"),
    ('185.15', 'disinctis', 'discinctis'),
    ('212.35', 'fu fù._', 'fu fò._'),
    ('230.15', 'Armentières.', 'Armentières.'),
    ('255.15', '_proculabeat_!', '_procul abeat_!'),
    ('257.28', 'tyzooysphal', 'ryzooysphal'),
    ('263.14', 'Espagnol', 'Espanol'),
    ('268.L07', 'Auctioneer', 'Auctioneer.'),
    ('271.07', ' OBIT. DIS', ''),
    ('272.F01', "that, ma'am, says", "that, ma'am? says"),
    ('273.F06', 'Well,Maggy,', 'Well, Maggy,'),
    ('275.14', 'Blowyheart', 'Blowyhart'),
    ('316.08', 'Whiyle', 'While'),
    ('345.18', 'skattert,had', 'skattert, had'),
    ('349.11', 'misseldhropes', 'missledhropes'),
    ('352.21', 'liking-cabronne! -- he', 'liking-cabronne! -he'),
    ('352.29', 'ahs!)', 'ahs!_)'),
    ('386.35', 'hopolopocattles', 'hopolopocattls'),
    ('418.04', 'l.s.d! Divi gloriam_.', 'l.s.d.! Divi gloriam_.'),
    ('418.21', 'the price of your save', 'the prize of your save'),
    ('437.29', 'Mazourikawitch of some', 'Mazourikawitch or some'),
    ('461.32', 'ah ah ah ah . . ..', 'ah ah ah ah. . . .'),
    ('481.02', 'Changechild . . .. . .. . .. . .. . ..?', 'Changechild ................?'),
    ('481.03', 'earth . . .. . .. . .. . .. . .. . .. . ..?_', 'earth ......................?_'),
    ('506.26', 'thorneyborn', 'thornyborn'),
    ('517.30', 'elven thirsty', 'eleven thirsty'),
    ('532.11', 'by Sal and', 'by Sall and'),
    ('538.22', 'Missy Mycock', 'Lissy Mycock'),
    ('548.28', 'Primamére', 'Primamère'),
    ('614.08', 'mornenslaund', 'mournenslaund'),
    ('304.04', 'Slutningsbane.2', 'Slutningsbane2.'),
    ('032.24', '_Loots in his_ _(bassvoco) _Boots_', '_Loots in his_ (bassvoco) _Boots_'),
    ('233.20', 'to ernest: to ernest:', 'to ernest:'),
    # Both transcriptions wrong; both scans agree (found by reocr.py on the
    # words where the scans agree against the text).
    ('310.07', 'megcycles', 'megacycles'),
    ('508.20', 'aquilities', 'aquilties'),
    ('590.10', 'How do you', 'How you do'),
    ('395.04', 'away a parchment', 'away at a parchment'),
    ('071.10', 'turv:', 'turv):'),
    ('614.29', 'shoolboy', 'schoolboy'),
    ('618.22', 'And,personably', 'And, personably'),
    ('276.25', 'bodgebox7', 'bodgbox7'),
    ('287.08', 'A.I.', 'A.1.'),
    ('290.18', '_O alors_!,', '_O alors!_,'),
    ('294.24', 'papcocopotl', 'papacocopotl'),
    ('298.07', 'dismissage', 'dimissage'),
    ('270.01', 'future1', 'future.1'),
    ('292.11', 'by cows . man', 'by cows ∵ man'),
    ('292.12', 'and {} they', 'and ∴ they'),
    ('300.08', 'be,carrotty!2', 'be, carrotty!2'),
    ('281.10', 'brisées, leur', 'brisées, leurs'),
    ('281.L03', 'Two Dons Johns', 'Twos Dons Johns'),
    # Sigla and other special characters, checked against both scans. A
    # siglum is written as Fweet writes it, "*E*", and set in the Fweet Figla
    # font (see fw.conf); the forms that the font lacks are written with the
    # closest Unicode characters.
    ('006.32', 'platterplate.', 'platterplate. *M*'),
    ('018.36', '{F}ace to {F}ace', 'Ⅎace to Ⅎace'),
    ('036.17', '~!)', 'Ǝ!)'),
    ('095.12', 'H2 C E3', 'H₂ C E₃'),
    ('119.17', '{E},', '*E*,'),
    ('119.19', '{A},', '*A*,'),
    ('121.03', '{F}', '\u2132'),
    ('121.07', 'suggestion, F,', 'suggestion, Ⅎ,'),
    ('124.09', '{V}', '*V*'),
    ('124.10', 'profèssionally', 'profèššionally'),
    ('238.07', '{feem}', 'ſeem'),
    ('238.08', '{elfewhere}', 'elſewhere'),
    ('238.08', "{pafs'd}", "paſs'd"),
    ('238.08', '{fufpens}', 'ſuſpens'),
    ('266.22', 'F ■,', 'F ꟻ,'),
    ('284.11', '{8},', '∞,'),
    ('284.26', '{NCR}5', 'nCr5'),
    ('285.15', 'MPM', 'mPm'),
    ('298.13', '{THan}', 'THan'),
    ('298.13', '{thAN}', 'tHaN'),
    ('299.F05', 'family, Hoodle', 'family, *E*, *A*, *I*, *X*, *F*, *V*, *C*. Hoodle'),
]

LINES = {
    # The line division of 1958 (the transcriptions follow neither printing).
    '427.21' : 'and porpoise plain, from carnal relations undfamiliar faces, to the',
    '427.22' : 'inds of Tuskland where the oliphants scrum till the ousts of',
    '427.23' : 'Amiracles where the toll stories grow proudest, more is the pity,',
    '427.24' : 'but for all your deeds of goodness you were soo ooft and for',
    '427.25' : 'ever doing, manomano and myriamilia even to mulimuli, as',
}

# Whole components replaced: "PPP.K" (K is one of main, L, R, F) to the
# list of lines. A line "[[img:FILE]] CAPTION" is a figure (in img/).
COMPONENTS = {
    '292.L' : [],
    '269.L' : ['Undante', 'umoroso.', 'M. 50-50.', 'οὐκ ἔλαβον', 'πόλιν'],
    '272.L' : ['Pige pas.', '[[img:music-272.png]]', 'Seidlitz powther', 'for slogan', 'plumpers.', 'Hoploits and', 'atthems.'],
    '281.R' : ['THE PART', 'PLAYED BY', 'BELLETRI-', 'STICKS IN', 'THE BELLUM-', 'PAX-BEL-', 'LUM.', 'MUTUOMOR-',
               'PHOMUTA-', 'TION.', 'SORTES VIR-', 'GINIANAE.', 'INTERROGATION.', 'EXCLAMATION.'],
    '286.L' : ['Vive Paco', 'Hunter!', 'The hoisted in', 'red and the low-', 'ered in black.', "The boss's bess",
               'bass is the browd', 'of Mullingar.', 'The aliments of', 'jumeantry.'],
    '308.main' : ['Delays are Dangerous. Vitavite! Gobble', "Anne: tea's set, see's eneugh! Mox soonly",
                  'will be in a split second per the chancellory', 'of his exticker.',
                  'Aun', 'Do', 'Tri', 'Car', 'Cush1', 'Shay', 'Shockt', 'Ockt', 'Ni', 'Geg2', 'Their feed begins.',
                  'NIGHTLETTER',
                  'With our best youlldied greedings to Pep', 'and Memmy and the old folkers below and',
                  'beyant, wishing them all very merry Incar-', 'nations in this land of the livvey and plenty',
                  'of preprosperousness through their coming', 'new yonks', 'from',
                  'jake, jack and little sousoucie', '(the babes that mean too)'],
    '308.L' : ['Xenophon.', 'Pantocracy.', 'Bimutualism.', 'Interchangeabil-', 'ity. Naturality.', 'Superfetation.',
               'Stabimobilism.', 'Periodicity.', 'Consummation.', 'Interpenetrative-', 'ness. Predicam-',
               'ent. Balance of', 'the factual by the', 'theoric Boox and', 'Coox, Amallaga-', 'mated.',
               '[[img:hand-308.png]]', '[[img:bones-308.png]]'],
    '308.R' : ['MAWMAW,', 'LUK, YOUR', "BEEEFTAY'S", 'FIZZIN OVER!', 'KAKAO-', 'POETIC', 'LIPPUDENIES', 'OF THE',
               'UNGUMP-', 'TIOUS.'],
    '308.F' : ['1 Kish is for anticheirst, and the free of my hand to him!',
               "2 And gags for skool and crossbuns and whopes he'll enjoyimsolff over", 'our drawings on the line!'],
}

# Lines inserted: (reference of the new line, text).
INSERTS = [
    ('044.25', '[[img:score-044.png]] Have you heard of one Humpty Dumpty how he fell with a roll and a rumble '
               'and curled up like Lord Olafa Crumple by the butt of the Magazine Wall of the Magazine Wall '
               'Hump helmet and all Da Capo'),
    ('293.12', '[[img:figure-293.png]]'),
    ('292.32', 'somewhawre)'),
]

# Centred lines not detected from the geometry of the scan.
CENTER = ['044.22', '044.23', '044.24', '308.16', '308.23', '308.24', '308.25']

def center(text):
    for r in CENTER:
        (p, comp, n) = parse(r)
        text[p][comp][n - 1]['center'] = True

def ref(p, comp, n):
    return '{:03d}.{}{:02d}'.format(p, '' if comp == 'main' else comp, n)

def parse(r):
    (p, rest) = r.split('.')
    comp = 'main' if rest[0].isdigit() else rest[0]
    return int(p), comp, int(rest.lstrip('LRF'))

def apply(text, log):
    for (r, t) in INSERTS:
        (p, comp, n) = parse(r)
        rec = { 'kind' : 'override', 'was' : '', 'now' : t }
        text[p][comp].insert(n - 1, { 't' : t, 'p' : False, 'c' : [rec] })
        log.append(dict(rec, page = p, comp = comp, line = n))
    for (r, old, new) in SUBST:
        (p, comp, n) = parse(r)
        line = text[p][comp][n - 1]
        if old not in line['t'] and new in line['t']:
            continue    # Already established by the collation.
        if old not in line['t']:
            raise ValueError('override {}: "{}" not in "{}"'.format(r, old, line['t']))
        if old != new:
            t = line['t'].replace(old, new, 1)
            rec = { 'kind' : 'override', 'was' : line['t'], 'now' : t }
            line['c'].append(rec)
            log.append(dict(rec, page = p, comp = comp, line = n))
            line['t'] = t
    for (r, lines) in COMPONENTS.items():
        (p, comp) = r.split('.')
        p = int(p)
        was = [l['t'] for l in text[p][comp]]
        if was != lines:
            rec = { 'kind' : 'override', 'was' : ' / '.join(was), 'now' : ' / '.join(lines) }
            log.append(dict(rec, page = p, comp = comp, line = 0))
            text[p][comp] = [{ 't' : t, 'p' : False, 'c' : [rec] if i == 0 else [] } for (i, t) in enumerate(lines)]
    for (r, t) in LINES.items():
        (p, comp, n) = parse(r)
        line = text[p][comp][n - 1]
        if line['t'] != t:
            rec = { 'kind' : 'override', 'was' : line['t'], 'now' : t }
            line['c'].append(rec)
            log.append(dict(rec, page = p, comp = comp, line = n))
            line['t'] = t
