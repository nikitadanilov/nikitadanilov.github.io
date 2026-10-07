"""Facts from Fweet's line numbering rules (https://fweet.org/pages/fw_lnum.php),
used to validate the line structure of the deck."""

def ranges(s):
    out = []
    for r in s.replace(' ', '').split(','):
        a, _, b = r.partition('-')
        out += list(range(int(a), int(b or a) + 1))
    return out

# Pages with exactly 36 (or 37) main text lines.
FULL36 = set(ranges('004-029, 031-043, 049-073, 076-101, 105-124, 127-167, 170-174, 176-194,'
                    '197-215, 220-258, 310-340, 343-344, 347-348, 351-352, 354-381, 384-397,'
                    '404-417, 420-427, 430-472, 475-500, 502-527, 529-553, 556-562, 564-589,'
                    '594-627'))
FULL37 = { 528, 563 }

# Pages with footnotes, left and right marginalia in II.2.
HAS_F = set(ranges('260-279, 281-308'))
HAS_L = set(ranges('260-278, 280-287, 293-308'))
HAS_R = set(ranges('260-262, 264, 266-268, 270-272, 275-276, 278-279, 281-282, 286, 293, 300,'
                   '302-306, 308'))

# Verses printed with a hanging indent: (page, line) of the verse whose
# continuation lines are merged into it.
VERSES = { 45 : [25, 28], 46 : [7, 17, 23, 25], 175 : [7, 8, 10, 11, 13, 14, 15, 16, 17, 18],
           383 : [6], 398 : [32, 33], 399 : [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 16] }

def expected(p):
    return 36 if p in FULL36 else 37 if p in FULL37 else None
