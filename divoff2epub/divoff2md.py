# -*- coding: utf-8 -*-

"""
TODO:
* eundem/eundem w plikach zrodlowych
"""
import contextlib
import sys
import re
import os
import argparse
from collections import OrderedDict
from consts import DIVOFF_DIR, TRANSLATION, \
    TRANSLATION_MULTI, TRANSFORMATIONS, EXCLUDE_SECTIONS, EXCLUDE_SECTIONS_TITLES, \
    DIVOFF_DIR, PROPERS_INPUT, REFERENCE_REGEX, SECTION_REGEX, LANG1, LANG2, MD_OUTPUT_DIR, THIS_DIR
import logging
import sys


logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s')
log = logging.getLogger(__name__)


@contextlib.contextmanager
def smart_open(filename=None):
    if filename:
        fh = open(filename, 'a')
    else:
        fh = sys.stdout

    try:
        yield fh
    finally:
        if fh is not sys.stdout:
            fh.close()


def normalize(ln, lang):
    for r, s in TRANSFORMATIONS:
        ln = re.sub(r, s.get(lang, s.get(None)), ln)
    return ln


def strip_contents(d):
    for section, content in d.items():
        while content and not content[-1]:
            content.pop(-1)
    return d


def get_full_path(partial_path, lang):
    full_path = os.path.join('.', 'data', 'divinum-officium', 'web', 'www', 'missa', lang, partial_path)
    if not os.path.exists(full_path):
        full_path = os.path.join(DIVOFF_DIR, 'web', 'www', 'missa', lang, partial_path)
    return full_path


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


def parse_file(partial_path, lang=LANG1, lookup_section=None):
    """
    Read the file and organize the content as ordered dictionary
    where `[Section]` becomes a key and each line below - an item of related
    list. Resolve references like `@Sancti/02-02:Evangelium`.
    """
    d = OrderedDict()
    section = None
    concat_line = False
    full_path = get_full_path(partial_path, lang)
    with open(full_path) as fh:
        for itr, ln in enumerate(fh):
            ln = ln.strip()

            if section is None and ln == '':
                # Skipping empty lines in the beginning of the file
                continue

            if section is None and REFERENCE_REGEX.match(ln):
                # reference outside any section as a first non-empty line - load all sections
                # from the referenced file and continue with the sections from the current one.
                path_bit, _, _ = REFERENCE_REGEX.findall(ln)[0]
                # Recursively read referenced file
                nested_path = get_full_path(path_bit + '.txt', lang) if path_bit else partial_path
                d = parse_file(nested_path)
                continue

            ln = normalize(ln, lang)

            if re.search(SECTION_REGEX, ln):
                section = re.sub(SECTION_REGEX, '\\1', ln)

            if not lookup_section or lookup_section == section:
                if re.match(SECTION_REGEX, ln):
                    d[section] = []
                else:
                    if REFERENCE_REGEX.match(ln):
                        path_bit, nested_section, substitution = REFERENCE_REGEX.findall(ln)[0]
                        if path_bit:
                            # Reference to external file - parse it recursively
                            nested_path = get_full_path(path_bit + '.txt', lang) if path_bit else partial_path
                            nested_content = parse_file(nested_path, lookup_section=nested_section)
                            try:
                                d[section].extend(nested_content[nested_section])
                            except KeyError:
                                log.warning("Section `%s` referenced from `%s` is missing in `%s`",
                                            nested_section, full_path, nested_path)
                        else:
                            # Reference to the other section in current file
                            d[section].extend(d[nested_section])
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


def write_contents(out_path, contents, in_partial_path='', pref='', comm='', stdout=False):

    def _write_section(section, lines, fh):
        fh.write('\n\n')
        if section not in EXCLUDE_SECTIONS_TITLES:
            fh.write('### ' + translation.get(section, section) + '  \n')
        for line in lines:
            fh.write(line + '  \n')
            if section == 'Comment' and line.startswith('## ') and img_exists:
                fh.write('\n<div style="text-align:center"><img src ="{}" /></div>\n\n'.format(img_path))

    with smart_open(out_path if not stdout else None) as fh:

        if isinstance(contents, list):
            for ln in contents:
                fh.write(ln.strip() + '\n')
            return

        img_path = get_full_path(in_partial_path.replace('txt', 'png'), LANG1)
        img_exists = os.path.exists(img_path)

        # Preparing translations
        translation = {}
        translation.update(TRANSLATION)
        if 'GradualeL1' in contents.keys():
            translation.update(TRANSLATION_MULTI)

        # Printing sections
        for section, lines in contents.items():
            if section in EXCLUDE_SECTIONS:
                continue
            _write_section(section, lines, fh)

            # After Secreta print Prefation and (optionally) Communicantes
            if section == 'Secreta':
                _write_section('Prefatio', pref, fh)
                if comm:
                    _write_section('Communicantes', comm, fh)

        if 'Ordo' not in in_partial_path:
            fh.write('■\n')


def main(input_=PROPERS_INPUT, stdout=False):
    log.info("Starting the process")
    log.debug("Reading Ordo/Prefationes.txt")
    prefationes = parse_file('Ordo/Prefationes.txt')
    for i, block in enumerate(input_, 1):
        out_path = os.path.join(MD_OUTPUT_DIR, "{:02}.md".format(i))
        if os.path.exists(out_path) and not stdout:
            os.remove(out_path)
        for item in block:
            if len(item) == 1:
                # Printing season's title
                write_contents(out_path, ['\n\n', '# ' + item[0]], stdout=stdout)
                log.info("Processing block `%s`", item[0])
            else:
                # Printing propers
                in_partial_path, pref_key, comm_key = item
                try:
                    log.debug("Parsing file `%s`", in_partial_path)
                    contents = parse_file(in_partial_path, LANG1)
                    # TODO: local latin translation for Polish particular days
                    # try:
                    #     contents2 = parse_file(in_path, LANG2)
                    # except FileNotFoundError:
                    #     if 'pl' in in_path:
                    #         pass
                    #     else:
                    #         raise
                except Exception as e:
                    log.error("Cannot parse file `%s`: %s", in_partial_path, e)
                    raise
                else:
                    log.debug("Writing file `%s`", out_path)
                    write_contents(out_path, contents, in_partial_path, prefationes.get(pref_key),
                                   prefationes.get(comm_key), stdout=stdout)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("file_name", nargs='?', default=argparse.SUPPRESS,
                        help="File name containing given proper from divinumofficium, "
                             "e.g. web/www/missa/Polski/Sancti/11-11.txt")
    parser.add_argument("--pref_key",
                        default="Communis", help="Prefacio, e.g. Trinitate")
    parser.add_argument("--comm_key",
                        help="Commune, e.g. C-Nat1962")
    parser.add_argument("--stdout", action='store_true',
                        help="Write to stdout instead of writing to the files.")
    args = parser.parse_args()
    if 'file_name' not in args:
        main(stdout=args.stdout)
    else:
        main((((args.file_name, args.pref_key, args.comm_key), ), ), stdout=args.stdout)

