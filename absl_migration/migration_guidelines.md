# gflags to absl.flags Migration Guidelines

The [python-gflags](https://github.com/google/python-gflags) library has been merged into [Abseil Python Common Libraries](https://github.com/abseil/abseil-py).
As a result, python-gflags will no longer be maintained.
This document tries to help explain how to migrate from `gflags` to `absl.flags`.

Note if your upstream dependencies have been migrated to `absl.flags`,
we encourage you also migrating to <code>[absl.flags](https://github.com/abseil/abseil-py/tree/master/absl/flags)</code>.
Otherwise there will be two global `FLAGS` objects coexisting in the same process.
Both of them define flags and need to parse command-line args.

## Changes

This section lists the majors changes in absl.flags.

### API Renaming

1.  Except the `DEFINE` functions, other method and function names are updated so they conform to PEP8 snake_case style.
1.  `DEFINE_multistring` and `DEFINE_multti_int` are renamed to `DEFINE_multi_string` and `DEFINE_multti_integer`, for consistency.
1.  Exceptions are renamed so they end with `Error`.  Also `FlagsError` renamed to `Error`.
1.  All sub-modules have been made private, the public APIs should only be accessed at the package level.

### Behavior Changes

1.  Flags now use [GNU-style](https://docs.python.org/3/library/getopt.html#getopt.gnu_getopt) parsing by default. To opt-in to non-GNU style, call `FLAGS.set_gnu_getopt(False)` before parsing flags.
1.  Accessing flag values before command-line args are parsed now raises the `UnparsedFlagAccessError`.
1.  It is no longer legal to define a flag with a  default value type that mismatches the flag type.
1.  `FLAGS.set_default` no longer overrides the current value if the flag is set by `FLAGS.name = value`, or specified in the command line.

## Migration Guidelines

We suggest the following steps for migrating from `gflags` to `absl.flags`:

1.  Upgrade to the latest python-gflags version, which contains the new API names (see [Appendix](#appendix-renamed-apis)).
1.  Update the codebase to use the new APIs.
    * You can leverage [migrate.py](migrate.py) to perform the renames and sanity checks. Be aware that it only uses regex matching, which may have false positives or miss some cases.
1.  Remove the dependency on [python-gflags](https://pypi.python.org/pypi/python-gflags) and add the dependency on [absl-py](https://pypi.python.org/pypi/absl-py). Then replace `import gflags` with `from absl import flags as gflags`.
1.  Once step (3) succeeds, remove the import alias and just use `flags`.

Depending on your project, you can choose to do these at once, or make incremental changes.

## Appendix: Renamed APIs

Here is a list of renamed APIs:

```
DEFINE_multistring -> DEFINE_multi_string
DEFINE_multi_int -> DEFINE_multi_integer
RegisterValidator -> register_validator
Validator -> validator
RegisterMultiFlagsValidator -> register_multi_flags_validator
MultiFlagsValidator -> multi_flags_validator
MarkFlagAsRequired -> mark_flag_as_required
MarkFlagsAsRequired -> mark_flags_as_required
MarkFlagsAsMutualExclusive -> mark_flags_as_mutual_exclusive
DECLARE_key_flag -> declare_key_flag
ADOPT_module_key_flags -> adopt_module_key_flags
DISCLAIM_key_flags -> disclaim_key_flags
GetHelpWidth -> get_help_width
TextWrap -> text_wrap
FlagDictToArgs -> flag_dict_to_args
DocToHelp -> doc_to_help
FlagsError -> Error
IllegalFlagValue -> IllegalFlagValueError
ArgumentParser.Parse -> ArgumentParser.parse
ArgumentParser.Type -> ArgumentParser.flag_type
FLAGS.AppendFlagsIntoFile -> FLAGS.append_flags_into_file
FLAGS.AppendFlagValues -> FLAGS.append_flag_values
FLAGS.FindModuleDefiningFlag -> FLAGS.find_module_defining_flag
FLAGS.FindModuleIdDefiningFlag -> FLAGS.find_module_id_defining_flag
FLAGS.FlagsByModuleDict -> FLAGS.flags_by_module_dict
FLAGS.FlagsByModuleIdDict -> FLAGS.flags_by_module_id_dict
FLAGS.FlagsIntoString -> FLAGS.flags_into_string
FLAGS.FlagValuesDict -> FLAGS.flag_values_dict
FLAGS.IsGnuGetOpt -> FLAGS.is_gnu_getopt
FLAGS.IsParsed -> FLAGS.is_parsed
FLAGS.KeyFlagsByModuleDict -> FLAGS.key_flags_by_module_dict
FLAGS.MainModuleHelp -> FLAGS.main_module_help
FLAGS.MarkAsParsed -> FLAGS.mark_as_parsed
FLAGS.ModuleHelp -> FLAGS.module_help
FLAGS.ReadFlagsFromFiles -> FLAGS.read_flags_from_files
FLAGS.RemoveFlagValues -> FLAGS.remove_flag_values
FLAGS.Reset -> FLAGS.unparse_flags
FLAGS.SetDefault -> FLAGS.set_default
FLAGS.WriteHelpInXMLFormat -> FLAGS.write_help_in_xml_format
```
