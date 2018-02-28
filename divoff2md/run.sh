python parser.py  > md/mszalik.md
pandoc --epub-chapter-level=2 --epub-stylesheet=style.css --epub-cover-image=img/cover.png --epub-metadata=meta.xml --toc-depth=2 -o mszalik.epub md/title.md md/mszalik.md
#kindlegen mszalik.epub
open mszalik.epub
