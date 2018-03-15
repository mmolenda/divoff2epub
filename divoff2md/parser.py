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
    DIVOFF_DIR, PROPERS_INPUT, REF_REGEX, SECTION_REGEX, LANG1, OUTPUT_DIR
import logging
import sys


logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)


def normalize(ln, lang):
    for r, s in TRANSFORMATIONS:
        ln = re.sub(r, s.get(lang, s.get(None)), ln)
    return ln


def strip_contents(d):
    for section, content in d.items():
        while content and not content[-1]:
            content.pop(-1)
    return d


def get_full_path(path, lang):
    return os.path.join(DIVOFF_DIR, 'web', 'www', 'missa', lang, path)


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


def parse_file(path, lang=LANG1, lookup_section=None):
    """
    Read the file and organize the content as ordered dictionary
    where `[Section]` becomes a key and each line below - an item of related
    list. Resolve references like `@Sancti/02-02:Evangelium`.
    """
    d = OrderedDict()
    section = None
    concat_line = False
    full_path = path if os.path.exists(path) else get_full_path(path, lang)
    with open(full_path) as fh:
        for ln in fh:
            if section is None and ln.strip() == '':
                # Skipping empty lines in the beginning of the file
                continue
            ln = normalize(ln.strip(), lang)
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
                        nested_path = get_full_path(path_bit + '.txt', lang) if path_bit else path
                        nested_content = parse_file(nested_path, lookup_section=nested_section)
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
    d = strip_contents(d)
    d = resolve_conditionals(d)
    return d


def write_contents(out_path, contents, in_path='', pref='', comm=''):

    def _write_section(section, lines, fh):
        fh.write('\n\n')
        if section not in EXCLUDE_SECTIONS_TITLES:
            fh.write('### ' + translation.get(section, section) + '  \n')
        for line in lines:
            fh.write(line + '  \n')
            if section == 'Comment' and line.startswith('## ') and img_exists:
                fh.write('\n<div style="text-align:center"><img src ="{}" /></div>\n\n'.format(img_path))

    with open(out_path, 'a') as fh:

        if isinstance(contents, list):
            for ln in contents:
                fh.write(ln.strip() + '\n')
            return

        img_path = in_path.replace('txt', 'png')
        img_exists = os.path.exists(img_path)

        # Preparing translations
        translation = {}
        translation.update(TRANSLATION)
        if 'GradualeL1' in contents.keys():
            translation.update(TRANSLATION_MULTI)

        # Printing sections
        for section, lines in contents.items():
            _write_section(section, lines, fh)

            # After Secreta print Prefation and (optionally) Communicantes
            if section == 'Secreta':
                _write_section('Prefatio', pref, fh)
                if comm:
                    _write_section('Communicantes', comm, fh)

        if not in_path.startswith('Ordo'):
            fh.write('■\n')


def main(input_=PROPERS_INPUT):
    log.info("Starting the process")
    log.debug("Reading Ordo/Prefationes.txt")
    prefationes = parse_file('Ordo/Prefationes.txt')
    for i, block in enumerate(input_, 1):
        out_path = os.path.join(OUTPUT_DIR, "{:02}.md".format(i))
        try:
            os.remove(out_path)
        except OSError:
            pass
        for item in block:
            if len(item) == 1:
                # Printing season's title
                write_contents(out_path, ['\n\n', '# ' + item[0]])
                log.info("Processing block `%s`", item[0])
            else:
                # Printing propers
                in_path, pref_key, comm_key = item
                try:
                    log.debug("Parsing file `%s`", in_path)
                    contents = parse_file(in_path)
                except Exception as e:
                    log.error("Cannot parse file `%s`: %s", in_path, e)
                    raise
                else:
                    log.debug("Writing file `%s`", out_path)
                    write_contents(out_path, contents, in_path, prefationes.get(pref_key), prefationes.get(comm_key))

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

