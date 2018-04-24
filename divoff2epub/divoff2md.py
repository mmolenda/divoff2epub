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
    DIVOFF_DIR, PROPERS_INPUT, REFERENCE_REGEX, SECTION_REGEX, POLSKI, LATIN, MD_OUTPUT_DIR, THIS_DIR, \
    FOOTNOTE_REF_REGEX, FOOTNOTE_REGEX
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


class Divoff(object):

    prefationes_a = None
    prefationes_b = None
    footnotes = []

    def run(self, input_, stdout):
        log.info("Starting the process")
        log.debug("Reading Ordo/Prefationes.txt")
        self.prefationes_a = self.parse_file('Ordo/Prefationes.txt')
        self.prefationes_b = self.parse_file('Ordo/Prefationes.txt', lang=LATIN) if LATIN else {}
        for i, block in enumerate(input_, 1):
            out_path = os.path.join(MD_OUTPUT_DIR, "{:02}.md".format(i))
            if os.path.exists(out_path) and not stdout:
                os.remove(out_path)
            for item in block:
                if len(item) == 1:
                    # Printing season's title
                    self.write_contents(out_path, ['\n\n', '# ' + item[0]], None, stdout=stdout)
                    log.info("Processing block `%s`", item[0])
                else:
                    # Printing propers
                    in_partial_path, pref_key, comm_key = item
                    try:
                        log.debug("Parsing file `%s`", in_partial_path)
                        contents_a = self.parse_file(in_partial_path, POLSKI)
                        contents_b = self.parse_file(in_partial_path, LATIN) if LATIN else {}
                    except Exception as e:
                        log.error("Cannot parse file `%s`: %s", in_partial_path, e)
                        raise
                    else:
                        log.debug("Writing file `%s`", out_path)
                        self.write_contents(out_path, contents_a, contents_b, in_partial_path, pref_key,
                                            comm_key, stdout=stdout)

        if self.footnotes:
            fn_path = os.path.join(MD_OUTPUT_DIR, "footnotes.md")
            if os.path.exists(fn_path) and not stdout:
                os.remove(fn_path)
            with smart_open(fn_path if not stdout else None) as fh:
                for footnote_itr, footnote in enumerate(self.footnotes, 1):
                    fh.write('[^{}]: {}\n'.format(footnote_itr, footnote))

    def parse_file(self, partial_path, lang=POLSKI, lookup_section=None):
        """
        Read the file and organize the content as ordered dictionary
        where `[Section]` becomes a key and each line below - an item of related
        list. Resolve references like `@Sancti/02-02:Evangelium`.
        """
        d = OrderedDict()
        section = None
        concat_line = False
        full_path = self._get_full_path(partial_path, lang)
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
                    nested_path = self._get_full_path(path_bit + '.txt', lang) if path_bit else partial_path
                    d = self.parse_file(nested_path)
                    continue

                ln = self._normalize(ln, lang)

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
                                nested_path = self._get_full_path(path_bit + '.txt', lang) if path_bit else partial_path
                                nested_content = self.parse_file(nested_path, lookup_section=nested_section)
                                try:
                                    d[section].extend(nested_content[nested_section])
                                except KeyError:
                                    log.warning("Section `%s` referenced from `%s` is missing in `%s`",
                                                nested_section, full_path, nested_path)
                            else:
                                # Reference to the other section in current file
                                d[section].extend(d[nested_section])
                        else:
                            # Finally, a regular line...
                            # Line ending with `~` indicates that next line
                            # should be treated as its continuation
                            appendln = ln.replace('~', ' ')
                            if concat_line:
                                d[section][-1] += appendln
                            else:
                                d[section].append(appendln)
                            concat_line = True if ln.endswith('~') else False
        d = self._strip_contents(d)
        d = self._resolve_conditionals(d)
        return d

    def write_contents(self, out_path, contents_a, contents_b, in_partial_path='', pref='', comm='', stdout=False):

        def _write_section(contents_a, section, lines_a, lines_b, fh):
            fh.write('\n\n')
            if section not in EXCLUDE_SECTIONS_TITLES:
                fh.write('### ' + translation.get(section, section) + '  \n')
            for i, line in enumerate(lines_a, 1):
                # Handling footnote defined in-line
                if re.search(FOOTNOTE_REF_REGEX, line):
                    self.footnotes.append(re.sub(FOOTNOTE_REGEX, '', contents_a['Footnotes'].pop(0)))
                    line = re.sub(FOOTNOTE_REF_REGEX, '[^{}]'.format(len(self.footnotes)), line)

                if i < len(lines_a):
                    # Newline after each line but last
                    fh.write(line + '   \n')
                else:
                    # Generate footnote out of respective Latin translation
                    if lines_b:
                        self.footnotes.append(' '.join(lines_b))
                        fh.write(line + '[^{}]'.format(len(self.footnotes)) + '   \n')
                    else:
                        fh.write(line + '   \n')
                if section == 'Comment' and line.startswith('## ') and img_exists:
                    fh.write('\n<div style="text-align:center"><img src ="{}" /></div>\n\n'.format(img_path))

        with smart_open(out_path if not stdout else None) as fh:
            if isinstance(contents_a, list):
                for ln in contents_a:
                    fh.write(ln.strip() + '\n')
                return

            img_path = self._get_full_path(in_partial_path.replace('txt', 'png'), POLSKI)
            img_exists = os.path.exists(img_path)

            # Preparing translations
            translation = {}
            translation.update(TRANSLATION)
            if 'GradualeL1' in contents_a.keys():
                translation.update(TRANSLATION_MULTI)

            # Printing sections
            for section_a, lines_a in contents_a.items():
                if section_a in EXCLUDE_SECTIONS:
                    continue

                # Before Communio print Prefatio and (optionally) Communicantes
                if section_a == 'Communio':
                    _write_section(contents_a, 'Prefatio', self.prefationes_a[pref], self.prefationes_b.get(pref), fh)
                    if comm:
                        _write_section(contents_a, 'Communicantes', self.prefationes_a[comm], self.prefationes_b.get(comm), fh)

                lines_b = contents_b.get(section_a)
                _write_section(contents_a, section_a, lines_a, lines_b, fh)

            if 'Ordo' not in in_partial_path:
                fh.write('■\n')

    @staticmethod
    def _normalize(ln, lang):
        for r, s in TRANSFORMATIONS:
            ln = re.sub(r, s.get(lang, s.get(None)), ln)
        return ln

    @staticmethod
    def _strip_contents(d):
        for section, content in d.items():
            while content and not content[-1]:
                content.pop(-1)
        return d

    @staticmethod
    def _get_full_path(partial_path, lang):
        if os.path.exists(partial_path):
            return partial_path
        full_path = os.path.join('.', 'data', 'divinum-officium-custom', 'web', 'www', 'missa', lang, partial_path)
        if not os.path.exists(full_path):
            full_path = os.path.join('.', 'data', 'divinum-officium', 'web', 'www', 'missa', lang, partial_path)
        return full_path

    @staticmethod
    def _resolve_conditionals(d):
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


def main(input_=PROPERS_INPUT, stdout=False):
    divoff = Divoff()
    divoff.run(input_, stdout)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("file_names", nargs='*', default=argparse.SUPPRESS,
                        help="File names containing given proper from divinumofficium, "
                             "e.g. web/www/missa/Polski/Sancti/11-11.txt")
    parser.add_argument("--pref_key",
                        default="Communis", help="Prefacio, e.g. Trinitate")
    parser.add_argument("--comm_key",
                        help="Commune, e.g. C-Nat1962")
    parser.add_argument("--stdout", action='store_true',
                        help="Write to stdout instead of writing to the files.")
    args = parser.parse_args()
    if 'file_names' not in args:
        main(stdout=args.stdout)
    else:
        for file_name in args.file_names:
            main((((file_name, args.pref_key, args.comm_key), ), ), stdout=args.stdout)

