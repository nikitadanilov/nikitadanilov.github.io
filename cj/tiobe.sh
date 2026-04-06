#!/bin/bash

function parts() {
    local args=("$@")
    local n=${#args[@]}
    local i j
    for (( i = 0; i < n; ++i )); do
        for (( j = n; j > i + 3; --j )); do
            printf '%s\n' "${args[*]:i:j-i}"
        done
    done
}

while read ;do
    line=$REPLY
    parts $line | while read ;do
        part=$REPLY
        cat tiobe.txt | grep -- "$part" >/dev/null && echo "/ += . \"$part\" -> https://www.gutenberg.org/files/844/844-h/844-h.htm#:~:text=$(echo "$part" | sed 's/ /%20/g')"
    done
done
