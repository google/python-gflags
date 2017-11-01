#!/usr/bin/env python
"""Helper tool for gflags to absl.flags migration."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import os
import re


_MIGRATIONS = [
    (r'\b(g?flags\.)DEFINE_multistring\b', r'\1DEFINE_multi_string'),
    (r'\b(g?flags\.)DEFINE_multi_int\b', r'\1DEFINE_multi_integer'),
    (r'\b(g?flags\.)RegisterValidator\b', r'\1register_validator'),
    (r'\b(g?flags\.)Validator\b', r'\1validator'),
    (r'\b(g?flags\.)RegisterMultiFlagsValidator\b', r'\1register_multi_flags_validator'),
    (r'\b(g?flags\.)MultiFlagsValidator\b', r'\1multi_flags_validator'),
    (r'\b(g?flags\.)MarkFlagAsRequired\b', r'\1mark_flag_as_required'),
    (r'\b(g?flags\.)MarkFlagsAsRequired\b', r'\1mark_flags_as_required'),
    (r'\b(g?flags\.)MarkFlagsAsMutualExclusive\b', r'\1mark_flags_as_mutual_exclusive'),
    (r'\b(g?flags\.)DECLARE_key_flag\b', r'\1declare_key_flag'),
    (r'\b(g?flags\.)ADOPT_module_key_flags\b', r'\1adopt_module_key_flags'),
    (r'\b(g?flags\.)DISCLAIM_key_flags\b', r'\1disclaim_key_flags'),
    (r'\b(g?flags\.)GetHelpWidth\b', r'\1get_help_width'),
    (r'\b(g?flags\.)TextWrap\b', r'\1text_wrap'),
    (r'\b(g?flags\.)FlagDictToArgs\b', r'\1flag_dict_to_args'),
    (r'\b(g?flags\.)DocToHelp\b', r'\1doc_to_help'),
    (r'\b(g?flags\.)FlagsError\b', r'\1Error'),
    (r'\b(g?flags\.)IllegalFlagValue\b', r'\1IllegalFlagValueError'),
    (r'\bFLAGS\.AppendFlagsIntoFile\b', r'FLAGS.append_flags_into_file'),
    (r'\bFLAGS\.AppendFlagValues\b', r'FLAGS.append_flag_values'),
    (r'\bFLAGS\.FindModuleDefiningFlag\b', r'FLAGS.find_module_defining_flag'),
    (r'\bFLAGS\.FindModuleIdDefiningFlag\b', r'FLAGS.find_module_id_defining_flag'),
    (r'\bFLAGS\.FlagsByModuleDict\b', r'FLAGS.flags_by_module_dict'),
    (r'\bFLAGS\.FlagsByModuleIdDict\b', r'FLAGS.flags_by_module_id_dict'),
    (r'\bFLAGS\.FlagsIntoString\b', r'FLAGS.flags_into_string'),
    (r'\bFLAGS\.FlagValuesDict\b', r'FLAGS.flag_values_dict'),
    (r'\bFLAGS\.IsGnuGetOpt\b', r'FLAGS.is_gnu_getopt'),
    (r'\bFLAGS\.IsParsed\b', r'FLAGS.is_parsed'),
    (r'\bFLAGS\.KeyFlagsByModuleDict\b', r'FLAGS.key_flags_by_module_dict'),
    (r'\bFLAGS\.MainModuleHelp\b', r'FLAGS.main_module_help'),
    (r'\bFLAGS\.MarkAsParsed\b', r'FLAGS.mark_as_parsed'),
    (r'\bFLAGS\.ModuleHelp\b', r'FLAGS.module_help'),
    (r'\bFLAGS\.ReadFlagsFromFiles\b', r'FLAGS.read_flags_from_files'),
    (r'\bFLAGS\.RemoveFlagValues\b', r'FLAGS.remove_flag_values'),
    (r'\bFLAGS\.Reset\b', r'FLAGS.unparse_flags'),
    (r'\bFLAGS\.SetDefault\b', r'FLAGS.set_default'),
    (r'\bFLAGS\.WriteHelpInXMLFormat\b', r'FLAGS.write_help_in_xml_format'),
    (r'\bFLAGS\.UseGnuGetOpt\(use_gnu_getopt=', r'FLAGS.set_gnu_getopt(gnu_getopt='),
    (r'\bFLAGS\.UseGnuGetOpt\(', r'FLAGS.set_gnu_getopt('),
]


_LEGACY_APIS_RE = re.compile(
    r'\b('
    r'(g?flags\.DEFINE_multistring)|'
    r'(g?flags\.DEFINE_multi_int)|'
    r'(g?flags\.RegisterValidator)|'
    r'(g?flags\.Validator)|'
    r'(g?flags\.RegisterMultiFlagsValidator)|'
    r'(g?flags\.MultiFlagsValidator)|'
    r'(g?flags\.MarkFlagAsRequired)|'
    r'(g?flags\.MarkFlagsAsRequired)|'
    r'(g?flags\.MarkFlagsAsMutualExclusive)|'
    r'(g?flags\.DECLARE_key_flag)|'
    r'(g?flags\.ADOPT_module_key_flags)|'
    r'(g?flags\.DISCLAIM_key_flags)|'
    r'(g?flags\.GetHelpWidth)|'
    r'(g?flags\.TextWrap)|'
    r'(g?flags\.FlagDictToArgs)|'
    r'(g?flags\.DocToHelp)|'
    r'(g?flags\.FlagsError)|'
    r'(g?flags\.IllegalFlagValue)|'
    r'(FLAGS\.AppendFlagsIntoFile)|'
    r'(FLAGS\.AppendFlagValues)|'
    r'(FLAGS\.FindModuleDefiningFlag)|'
    r'(FLAGS\.FindModuleIdDefiningFlag)|'
    r'(FLAGS\.FlagsByModuleDict)|'
    r'(FLAGS\.FlagsByModuleIdDict)|'
    r'(FLAGS\.FlagsIntoString)|'
    r'(FLAGS\.FlagValuesDict)|'
    r'(FLAGS\.IsGnuGetOpt)|'
    r'(FLAGS\.IsParsed)|'
    r'(FLAGS\.KeyFlagsByModuleDict)|'
    r'(FLAGS\.MainModuleHelp)|'
    r'(FLAGS\.MarkAsParsed)|'
    r'(FLAGS\.ModuleHelp)|'
    r'(FLAGS\.ReadFlagsFromFiles)|'
    r'(FLAGS\.RemoveFlagValues)|'
    r'(FLAGS\.Reset)|'
    r'(FLAGS\.SetDefault)|'
    r'(FLAGS\.WriteHelpInXMLFormat)|'
    r'(from\ gflags\ import\ (argument_parser|exceptions|flag|flags_formatting_test|flags_unicode_literals_test|flagvalues|validators))'
    r')\b')


def run(root_dir, migrate):
    for root, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            filepath = os.path.join(root, filename)
            with open(filepath) as f:
                content = f.read()

            if migrate:
                new_content = content
                for m in _MIGRATIONS:
                    new_content = re.sub(m[0], m[1], new_content)
                if new_content != content:
                    with open(filepath, 'w') as f:
                        f.write(new_content)
                    content = new_content

            for index, line in enumerate(content.split('\n')):
                if _LEGACY_APIS_RE.search(line):
                    print('{}:{} {}'.format(filepath, index + 1, line))


def main():
    parser = argparse.ArgumentParser(
        description='A gflags -> absl.flags migration tool.')
    parser.add_argument('--migrate', dest='migrate', action='store_true')
    parser.set_defaults(migrate=False)
    parser.add_argument('--root_dir', dest='root_dir', required=True)
    args = parser.parse_args()

    run(args.root_dir, args.migrate)


if __name__ == '__main__':
    main()