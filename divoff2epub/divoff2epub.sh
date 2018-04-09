#!/bin/bash
ver=$(grep Wersja data/md/title.md | cut -d ' ' -f2)
python divoff2md.py
pandoc --epub-chapter-level=2 --css=data/md/style.css --epub-cover-image=data/md/img/cover.png --toc-depth=2 -o data/ebook/mszalik-${ver}.epub data/md/title.md data/md/[0-9][0-9].md data/md/footnotes.md
#kindlegen data/ebook/mszalik-${ver}.epub
open data/ebook/mszalik-${ver}.epub
