# -*- coding: utf-8 -*-

"""
Example usage:
python divoff2md.py divinum-officium/web/www/missa/Polski/Sancti/02-02.txt /tmp/02-02.md
pandoc --epub-chapter-level=2 --toc-depth=2 -o /tmp/02-02.epub /tmp/02-02.md

TODO:
* GradualeP - uroczystosc serca J
* Munda Cor Passionis - N. Palmowa
* W. Czwartek, W. Piatek, Sobota Wielkanocna
* Pefacje, Communicantes
* Czesci stale
"""

import sys
import re
from collections import OrderedDict
from consts import DIVOFF_DIR, TRANSLATION, \
    TRANSLATION_MULTI, regexes, EXCLUDE_SECTIONS, EXCLUDE_SECTIONS_TITLES, \
    DIVOFF_DIR, PROPERS_INPUT

ref_regex = re.compile('^@(.*):(.*)')
section_regex = re.compile(r'^### *(.*)')

def normalize(ln):
    for r, s in regexes:
        ln = re.sub(r, s, ln)
    return ln


def read_file(path, lookup_section=None):
    d = OrderedDict()
    section = None
    with open(path) as fh:
        for ln in fh:
            ln = normalize(ln.strip())
            if re.search(section_regex, ln):
                section = re.sub(section_regex, '\\1', ln)

            if (not lookup_section and section not in EXCLUDE_SECTIONS) or \
               lookup_section == section:
                if re.match(section_regex, ln):
                    d[section] = []
                else:
                    ref_search_result = ref_regex.search(ln)
                    if ref_search_result:
                        path_bit, nested_section = ref_search_result.groups()
                        nested_path = DIVOFF_DIR + path_bit + '.txt' \
                                      if path_bit else path
                        nested_content = read_file(nested_path, nested_section)
                        d[section].extend(nested_content[nested_section])
                    else:
                        d[section].append(ln)
    return d

def print_contents(contents, pref, comm):

    def _print_section(section, lines):
        print '\n'
        if section not in EXCLUDE_SECTIONS_TITLES:
            print '### ' + translation.get(section, section) + '  '
        for line in lines:
            print line + '  '        

    # Preparing translations
    translation = {}
    translation.update(TRANSLATION)
    if 'GradualeL1' in contents.keys():
        translation.update(TRANSLATION_MULTI)

    # Printing sections    
    for section, lines in contents.items():
        _print_section(section, lines)

        # After Secreta print Prefation and (optionally) Communicantes
        if section == 'Secreta':
            _print_section('Prefatio', pref)
            if comm:
                _print_section('Communicantes', comm)

def main():
    prefationes = read_file(DIVOFF_DIR + 'Ordo/Prefationes.txt')
    for i in PROPERS_INPUT:
        if len(i) == 1:
            print '\n# ' + i[0]
        else:
            path, pref_key, comm_key = i
            try:
                contents = read_file(DIVOFF_DIR + path)
            except Exception, e:
                sys.stderr.write("Cannot parse {}: {}".format(sys.argv[1], e))
                raise
            else:
                print_contents(contents,
                               prefationes.get(pref_key),
                               prefationes.get(comm_key))

if __name__ == '__main__':
    main()
