#!/bin/sh
# Regenerate the deck (../*.deck, except the hand-written cards) from the
# witnesses (fetched by fetch.sh). The collation, with the record of every
# decision, is left in collation.json; the glosses of finwake.com located in
# the text in finwake.json.
set -e
cd "$(dirname "$0")"
python3 collate.py collation.json
python3 finwake.py collation.json finwake.json
python3 audio.py collation.json audio.json
python3 rose.py collation.json rose.json
python3 notons.py collation.json notons.json
python3 mkdeck.py collation.json ..
