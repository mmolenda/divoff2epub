# Divoff2md

Skrypt generuje Mszalik na niedziele i święta w formacie *epub* i *mobi* na podstawie plików źródłowych divinumofficium.com. Najpierw generowany jest plik `.md`, który następnie konwertowany jest do docelowych formatów.

## Wymagania

* python 2.7
* pandoc (http://pandoc.org/)
* kindlegen (https://www.amazon.com/gp/feature.html?docId=1000765211)

## Sposób użycia

* Ściągnij repozytorium https://github.com/DivinumOfficium/divinum-officium
* W pliku `consts.py` ustaw zmienną `DIVOFF_DIR` tak, aby wskazywała katalog z polskim tłumaczeniem Mszy
* Uruchom skrypt `run.sh`, który wygeneruje plik `md/mszalik.md` oraz `mszalik.epub` i `mszlik.kindle`

# Historia zmian

## v0.1

Pierwsza wersja mszalika

