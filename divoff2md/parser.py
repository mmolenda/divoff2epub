# -*- coding: utf-8 -*-

"""
TODO:
* eundem/eundem w plikach zrodlowych
"""

import sys
import re
import os
import argparse
from collections import OrderedDict
from consts import DIVOFF_DIR, TRANSLATION, \
    TRANSLATION_MULTI, TRANSFORMATIONS, EXCLUDE_SECTIONS, EXCLUDE_SECTIONS_TITLES, \
    DIVOFF_DIR, PROPERS_INPUT, REF_REGEX, SECTION_REGEX


def normalize(ln):
    for r, s in TRANSFORMATIONS:
        ln = re.sub(r, s, ln)
    return ln


def resolve_conditionals(d):
    for section, content in d.items():
        new_content = []
        omit = False
        itercontent = iter(content)
        for i, ln in enumerate(itercontent):
            if '(sed rubrica 1960 dicuntur)' in ln:
                # delete previous line; do not append current one
                del new_content[i - 1]
                continue
            if '(rubrica 1570 aut rubrica 1910 aut rubrica divino afflatu dicitur)' in ln:
                # skip next line; do not append current one
                next(itercontent)
                continue
            if '(deinde dicuntur)' in ln:
                # start skipping lines from now on
                omit = True
                continue
            if '(sed rubrica 1955 aut rubrica 1960 haec versus omittuntur)' in ln:
                # stop skipping lines from now on
                omit = False
                continue
            if omit:
                continue
            new_content.append(ln)
        d[section] = new_content
    return d


def read_file(path, lookup_section=None):
    """
    Read the file and organize the content as ordered dictionary
    where `[Section]` becomes a key and each line below - an item of related
    list. Resolve references like `@Sancti/02-02:Evangelium`.
    """
    d = OrderedDict()
    section = None
    concat_line = False
    full_path = path if os.path.exists(path) else DIVOFF_DIR + path
    with open(full_path) as fh:
        for ln in fh:
            ln = normalize(ln.strip())
            if re.search(SECTION_REGEX, ln):
                section = re.sub(SECTION_REGEX, '\\1', ln)

            if (not lookup_section and section not in EXCLUDE_SECTIONS) or \
                    (lookup_section == section):
                if re.match(SECTION_REGEX, ln):
                    d[section] = []
                else:
                    ref_search_result = REF_REGEX.search(ln)
                    if ref_search_result:
                        # Recursively read referenced file
                        path_bit, nested_section, substitution = ref_search_result.groups()
                        nested_path = DIVOFF_DIR + path_bit + '.txt' \
                                      if path_bit else path
                        nested_content = read_file(nested_path, nested_section)
                        d[section].extend(nested_content[nested_section])
                    else:
                        # Line ending with `~` indicates that next line
                        # should be treated as its continuation
                        appendln = ln.replace('~', ' ')
                        if concat_line:
                            d[section][-1] += appendln
                        else:
                            d[section].append(appendln)
                        concat_line = True if ln.endswith('~') else False
    d = resolve_conditionals(d)
    return d


def print_contents(path, contents, pref, comm):

    def _print_section(section, lines):
        print('\n')
        if section not in EXCLUDE_SECTIONS_TITLES:
            print('### ' + translation.get(section, section) + '  ')
        for line in lines:
            print(line + '  ')
            if section == 'Comment' and line.startswith('## ') and img_exists:
                print('\n<div style="text-align:center"><img src ="{}" /></div>\n'.format(img_path))

    img_path = path.replace('txt', 'png')
    img_exists = os.path.exists(img_path)
    
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

    if not path.startswith('Ordo'):
        print('■')

def main(input_=PROPERS_INPUT):
    prefationes = read_file('Ordo/Prefationes.txt')
    for i in input_:
        if len(i) == 1:
            # Printing season's title
            print('\n# ' + i[0])
        else:
            # Printing propers
            path, pref_key, comm_key = i
            try:
                contents = read_file(path)
            except Exception as e:
                sys.stderr.write("Cannot parse {}: {}\n".format(path, e))
                raise
            else:
                print_contents(path, contents,
                               prefationes.get(pref_key),
                               prefationes.get(comm_key))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("file_name", nargs='?', default=argparse.SUPPRESS,
                        help="File name containing given proper from divinumofficium, "
                             "e.g. web/www/missa/Polski/Sancti/11-11.txt")
    parser.add_argument("--pref_key",
                        default="Communis", help="Prefacio, e.g. Trinitate")
    parser.add_argument("--comm_key",
                        help="Commune, e.g. C-Nat1962")
    args = parser.parse_args()
    if 'file_name' not in args:
        main()
    else:
        main(((args.file_name, args.pref_key, args.comm_key), ))

