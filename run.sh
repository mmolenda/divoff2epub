python divoff2md.py  > mszalik.md
pandoc --epub-chapter-level=2 --epub-stylesheet=style.css --epub-cover-image=img/cover.png --epub-metadata=meta.xml --toc-depth=2 -o mszalik.epub title.md mszalik.md
kindlegen mszalik.epub
open mszalik.epub
