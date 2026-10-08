#!/bin/sh
# Fetch the witnesses of Finnegans Wake into $FWSRC (default ../src).
#
# The Oxford Text Archive is behind a bot challenge, so its two texts are
# fetched from the Wayback Machine; the scans come from archive.org.
set -e
TOOLS=$(cd "$(dirname "$0")" && pwd)
SRC=${FWSRC:-$TOOLS/../src}
mkdir -p "$SRC" && cd "$SRC"
WB=https://web.archive.org/web
IA=https://archive.org/download
curl -sL -o 1709.zip "$WB/20190116004213id_/http://ota.ox.ac.uk/text/1709.zip"
curl -sL -o 1696.zip "$WB/20190116005819id_/http://ota.ox.ac.uk/text/1696.zip"
unzip -o -q 1709.zip -d 1709
unzip -o -q 1696.zip -d 1696
curl -sL -o f1939_djvu.xml "$IA/in.ernet.dli.2015.207614/2015.207614.Finnegans-Wake_djvu.xml"
curl -sL -o f1939.pdf      "$IA/in.ernet.dli.2015.207614/2015.207614.Finnegans-Wake.pdf"
curl -sL -o v1958_djvu.xml "$IA/finneganswake00joycuoft/finneganswake00joycuoft_djvu.xml"
curl -sL -o v1958_page_numbers.json "$IA/finneganswake00joycuoft/finneganswake00joycuoft_page_numbers.json"
python3 "$TOOLS/djvu_lines.py" f1939_djvu.xml f1939_lines.json
python3 "$TOOLS/djvu_lines.py" v1958_djvu.xml v1958_lines.json
# Page images for the comparison of the printings (imgcmp.py and friends):
# the 1939 pages rendered from the PDF, the 1958 pages from archive.org.
mkdir -p f1939-pages v1958-pages
python3 -c "
import sys; sys.path.insert(0, '$TOOLS')
from witnesses import PAGES
print('\n'.join(str(p + 7) for p in PAGES))" |
    xargs -P 8 -I{} sh -c '[ -s f1939-pages/p{}.png ] || pdftoppm -f {} -l {} -r 300 -gray -png -singlefile f1939.pdf f1939-pages/p{}'
(cd "$TOOLS" && python3 -c "
from scans import v_pages
v = v_pages()
print('\n'.join(str(v[p]['scan']) for p in sorted(v)))") |
    xargs -P 8 -I{} sh -c "[ -s v1958-pages/n{}.jpg ] || curl -sL -o v1958-pages/n{}.jpg $IA/finneganswake00joycuoft/page/n{}.jpg"
# The text face (Source Serif 4), to compute the widths of the lines.
mkdir -p fonts
curl -sL -o fonts/SourceSerif4.ttf "https://fonts.gstatic.com/s/sourceserif4/v15/vEF02_tTDB4M7-auWDN0ahZJW1ge6NmXpVAHV83Bfb_US2D2QYxoUKIkn98pRl9dCw.ttf"
curl -sL -o fonts/SourceSerif4-Italic.ttf "https://fonts.gstatic.com/s/sourceserif4/v15/vEFy2_tTDB4M7-auWDN0ahZJW3IX2ih5nk3AucvUHf6OAVIJmeUDygwjihdqrhw.ttf"
# The chapters of finwake.com, whose glosses are linked from the notes.
mkdir -p finwake
for n in 1 2 3 4 5 6 7 8 21 22 23 24 31 32 33 34 41; do
    [ -s finwake/tekst$n.htm ] || curl -sL -o finwake/tekst$n.htm https://finwake.com/1024chapter$n/1024fwtekst$n.htm
    sleep 2
done
# The gloss pages of finwake.com, to check and repair the anchors of the links.
mkdir -p finwake/glosses
python3 -c "
import json
for u in sorted(set(x[4].split('#')[0] for x in json.load(open('$TOOLS/finwake.json')))): print(u)" |
    while read u; do
        f=$(echo ${u#https://finwake.com/} | tr / _)
        [ -s finwake/glosses/$f ] || { curl -sL -o finwake/glosses/$f "$u"; sleep 1; }
    done
# The automatic captions of the recorded readings (src/audio/readings.txt),
# to locate where they start. Needs yt-dlp (in ~/.venvs/fw, or $YTDLP).
grep -v '^#' audio/readings.txt | cut -d'|' -f1 | while read id; do
    [ -s audio/$id.en.vtt ] || ${YTDLP:-$HOME/.venvs/fw/bin/yt-dlp} -q --skip-download --write-auto-subs --sub-langs en --sub-format vtt -o "audio/%(id)s" "https://www.youtube.com/watch?v=$id"
    sleep 3
done
# The edition of 2010 (Rose and O'Hanlon) on the James Joyce Digital Archive:
# the pages "1939 -> 2010" of every section (the sections are listed in
# rose/sections.txt, collected from the menus of its chapter pages).
mkdir -p rose/cmp
sed -E 's|^\.\./||; s|^([a-z]+)10\.htm$|\1/\110.htm|' rose/sections.txt | while read p; do
    s=$(basename $p .htm)
    [ -s rose/cmp/$s.htm ] || curl -sL -o rose/cmp/$s.htm "https://jjda.ie/f/flex/$p"
    sleep 1
done
# The text of 1939 on the James Joyce Digital Archive, with its links to the
# notebooks (the "notons").
mkdir -p rose/l39
sed -E 's|^\.\./||; s|^([a-z]+)10\.htm$|\1/\110.htm|' rose/sections.txt | sed -E 's|^([a-z]+)/.*|\1|' | while read s; do
    [ -s rose/l39/$s.htm ] || curl -sL -o rose/l39/$s.htm "https://jjda.ie/f/flex/$s/l39$s.htm"
    sleep 1
done
