#!/bin/bash
ver=$(grep Wersja md/title.md | cut -d ' ' -f2)
python parser.py
pandoc --epub-chapter-level=2 --css=md/style.css --epub-cover-image=img/cover.png --toc-depth=2 -o mszalik-${ver}.epub md/title.md md/[0-9][0-9].md
#kindlegen mszalik-${ver}.epub
open mszalik-${ver}.epub
