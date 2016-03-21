#!/usr/bin/env python
# Copyright 2002 Google Inc. All Rights Reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""Helper functions for //gflags."""

import collections
import itertools
import os
import re
import struct
import sys
import textwrap
try:
  import fcntl  # pylint: disable=g-import-not-at-top
except ImportError:
  fcntl = None
try:
  # Importing termios will fail on non-unix platforms.
  import termios  # pylint: disable=g-import-not-at-top
except ImportError:
  termios = None

# pylint: disable=g-import-not-at-top
import gflags.third_party.pep257 as pep257


_DEFAULT_HELP_WIDTH = 80  # Default width of help output.
_MIN_HELP_WIDTH = 40  # Minimal "sane" width of help output. We assume that any
                      # value below 40 is unreasonable.

# Define the allowed error rate in an input string to get suggestions.
#
# We lean towards a high threshold because we tend to be matching a phrase,
# and the simple algorithm used here is geared towards correcting word
# spellings.
#
# For manual testing, consider "<command> --list" which produced a large number
# of spurious suggestions when we used "least_errors > 0.5" instead of
# "least_erros >= 0.5".
_SUGGESTION_ERROR_RATE_THRESHOLD = 0.50


# This is a set of module ids for the modules that disclaim key flags.
# This module is explicitly added to this set so that we never consider it to
# define key flag.
disclaim_module_ids = set([id(sys.modules[__name__])])



# Define special flags here so that help may be generated for them.
# NOTE: Please do NOT use SPECIAL_FLAGS from outside flags module.
# Initialized inside flagvalues.py.
SPECIAL_FLAGS = None


class _ModuleObjectAndName(
    collections.namedtuple('_ModuleObjectAndName', 'module module_name')):
  """Module object and name.

  Fields:
  - module: object, module object.
  - module_name: str, module name.
  """


def GetModuleObjectAndName(globals_dict):
  """Returns the module that defines a global environment, and its name.

  Args:
    globals_dict: A dictionary that should correspond to an environment
      providing the values of the globals.

  Returns:
    _ModuleObjectAndName - pair of module object & module name.
    Returns (None, None) if the module could not be identified.
  """
  name = globals_dict.get('__name__', None)
  module = sys.modules.get(name, None)
  # Pick a more informative name for the main module.
  return _ModuleObjectAndName(module,
                              (sys.argv[0] if name == '__main__' else name))


def GetCallingModuleObjectAndName():
  """Returns the module that's calling into this module.

  We generally use this function to get the name of the module calling a
  DEFINE_foo... function.

  Returns:
    The module object that called into this one.

  Raises:
    AssertionError: if no calling module could be identified.
  """
  range_func = range if sys.version_info[0] >= 3 else xrange
  for depth in range_func(1, sys.getrecursionlimit()):
    # sys._getframe is the right thing to use here, as it's the best
    # way to walk up the call stack.
    globals_for_frame = sys._getframe(depth).f_globals  # pylint: disable=protected-access
    module, module_name = GetModuleObjectAndName(globals_for_frame)
    if id(module) not in disclaim_module_ids and module_name is not None:
      return _ModuleObjectAndName(module, module_name)
  raise AssertionError('No module was found')


def GetCallingModule():
  """Returns the name of the module that's calling into this module."""
  return GetCallingModuleObjectAndName().module_name


# TODO(vrusinov): we should probably just use
# from __future__ import unicode_literals.
def StrOrUnicode(value):
  """Converts value to a python string or, if necessary, unicode-string."""
  try:
    return str(value)
  except UnicodeEncodeError:
    return unicode(value)


# TODO(vrusinov): this function must die.
def _MakeXMLSafe(s):
  """Escapes <, >, and & from s, and removes XML 1.0-illegal chars."""
  # Note that we cannot use cgi.escape() here since it is not supported by
  # Python 3.
  s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

  # Remove characters that cannot appear in an XML 1.0 document
  # (http://www.w3.org/TR/REC-xml/#charsets).
  #
  # NOTE: if there are problems with current solution, one may move to
  # XML 1.1, which allows such chars, if they're entity-escaped (&#xHH;).
  s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x80-\xff]', '', s)
  # Convert non-ascii characters to entities.  Note: requires python >=2.3
  s = s.encode('ascii', 'xmlcharrefreplace')   # u'\xce\x88' -> 'u&#904;'
  return s


def WriteSimpleXMLElement(outfile, name, value, indent):
  """Writes a simple XML element.

  Args:
    outfile: File object we write the XML element to.
    name: A string, the name of XML element.
    value: A Python object, whose string representation will be used
      as the value of the XML element.
    indent: A string, prepended to each line of generated output.
  """
  value_str = StrOrUnicode(value)
  if isinstance(value, bool):
    # Display boolean values as the C++ flag library does: no caps.
    value_str = value_str.lower()
  # TODO(vrusinov): we should use some lightweight built-in xml library instead
  # of hand-crafting xml.
  safe_value_str = _MakeXMLSafe(value_str)
  outfile.write('%s<%s>%s</%s>\n' % (indent, name, safe_value_str, name))


def GetHelpWidth():
  """Returns: an integer, the width of help lines that is used in TextWrap."""
  if not sys.stdout.isatty() or termios is None or fcntl is None:
    return _DEFAULT_HELP_WIDTH
  try:
    data = fcntl.ioctl(sys.stdout, termios.TIOCGWINSZ, '1234')
    columns = struct.unpack('hh', data)[1]
    # Emacs mode returns 0.
    # Here we assume that any value below 40 is unreasonable.
    if columns >= _MIN_HELP_WIDTH:
      return columns
    # Returning an int as default is fine, int(int) just return the int.
    return int(os.getenv('COLUMNS', _DEFAULT_HELP_WIDTH))

  except (TypeError, IOError, struct.error):
    return _DEFAULT_HELP_WIDTH


def GetMainModule():
  """Get the program name.  Do no use, this function is likely to be deleted.

  Returns:
    str, The name of the program.
  """
  # This is a poorly named internal API.  In the past it used to go crazy and
  # walk up the sys._getframe stack until it hit the top and call
  # GetModuleObjectAndName on that...  Meanwhile GetModuleObjectAndName was
  # always returning sys.argv[0] instead of anything related to the module as
  # the name of the top module is always __main__.  That logic was tripping
  # up an embedded Python launcher that uses a tiny module above __main__
  # to read, compile and exec __main__.  Solution: Simplify to sys.argv[0]!
  #
  # Flags only uses this to determine what flags to show in the short help
  # text and what to show as the program name.
  #
  # TODO(vrusinov): Delete this function entirely now that it is trivial.
  return sys.argv[0]


def GetFlagSuggestions(attempt, longopt_list):
  """Get helpful similar matches for an invalid flag."""
  # Don't suggest on very short strings, or if no longopts are specified.
  if len(attempt) <= 2 or not longopt_list:
    return []

  option_names = [v.split('=')[0] for v in longopt_list]

  # Find close approximations in flag prefixes.
  # This also handles the case where the flag is spelled right but ambiguous.
  distances = [(_DamerauLevenshtein(attempt, option[0:len(attempt)]), option)
               for option in option_names]
  distances.sort(key=lambda t: t[0])

  least_errors, _ = distances[0]
  # Don't suggest excessively bad matches.
  if least_errors >= _SUGGESTION_ERROR_RATE_THRESHOLD * len(attempt):
    return []

  suggestions = []
  for errors, name in distances:
    if errors == least_errors:
      suggestions.append(name)
    else:
      break
  return suggestions


def _DamerauLevenshtein(a, b):
  """Damerau-Levenshtein edit distance from a to b."""
  memo = {}

  def Distance(x, y):
    """Recursively defined string distance with memoization."""
    if (x, y) in memo:
      return memo[x, y]
    if not x:
      d = len(y)
    elif not y:
      d = len(x)
    else:
      d = min(
          Distance(x[1:], y) + 1,  # correct an insertion error
          Distance(x, y[1:]) + 1,  # correct a deletion error
          Distance(x[1:], y[1:]) + (x[0] != y[0]))  # correct a wrong character
      if len(x) >= 2 and len(y) >= 2 and x[0] == y[1] and x[1] == y[0]:
        # Correct a transposition.
        t = Distance(x[2:], y[2:]) + 1
        if d > t:
          d = t

    memo[x, y] = d
    return d
  return Distance(a, b)


def TextWrap(text, length=None, indent='', firstline_indent=None, tabs='    '):
  """Wraps a given text to a maximum line length and returns it.

  We turn lines that only contain whitespace into empty lines. We keep new
  lines.

  Args:
    text:             str, Text to wrap.
    length:           int, Maximum length of a line, includes indentation.
                      If this is None then use GetHelpWidth()
    indent:           str, Indent for all but first line.
    firstline_indent: str, Indent for first line; if None, fall back to indent.
    tabs:             ste, Replacement for tabs.

  Returns:
    Wrapped text.

  Raises:
    ValueError: if indent or firstline_indent not shorter than length.
  """
  # Get defaults where callee used None
  if length is None:
    length = GetHelpWidth()
  if indent is None:
    indent = ''
  if firstline_indent is None:
    firstline_indent = indent

  if len(indent) >= length:
    raise ValueError('Length of indent exceeds length')
  if len(firstline_indent) >= length:
    raise ValueError('Length of first line indent exceeds length')

  # TODO(vrusinov): tabs param is not used in flags, remove it altogether and
  # let textwrap use expandtabs().
  if tabs is None:
    tabs = ' '
  text = text.replace('\t', tabs)

  result = []
  # Create one wrapper for the first paragraph and one for subsequent
  # paragraphs that does not have the initial wrapping.
  wrapper = textwrap.TextWrapper(
      width=length, initial_indent=firstline_indent, subsequent_indent=indent)
  subsequent_wrapper = textwrap.TextWrapper(
      width=length, initial_indent=indent, subsequent_indent=indent)

  # textwrap does not have any special treatment for newlines. From the docs:
  # "...newlines may appear in the middle of a line and cause strange output.
  # For this reason, text should be split into paragraphs (using
  # str.splitlines() or similar) which are wrapped separately."
  for paragraph in (p.strip() for p in text.splitlines()):
    if paragraph:
      result.extend(wrapper.wrap(paragraph))
    else:
      result.append('')  # Keep empty lines.
    # Replace initial wrapper with wrapper for subsequent paragraphs.
    wrapper = subsequent_wrapper

  return '\n'.join(result)


def FlagDictToArgs(flag_map):
  """Convert a dict of values into process call parameters.

  This method is used to convert a dictionary into a sequence of parameters
  for a binary that parses arguments using this module.

  Args:
    flag_map: a mapping where the keys are flag names (strings).
      values are treated according to their type:
      * If value is None, then only the name is emitted.
      * If value is True, then only the name is emitted.
      * If value is False, then only the name prepended with 'no' is emitted.
      * If value is a string then --name=value is emitted.
      * If value is a collection, this will emit --name=value1,value2,value3.
      * Everything else is converted to string an passed as such.
  Yields:
    sequence of string suitable for a subprocess execution.
  """
  for key, value in flag_map.iteritems():
    if value is None:
      yield '--%s' % key
    elif isinstance(value, bool):
      if value:
        yield '--%s' % key
      else:
        yield '--no%s' % key
    elif isinstance(value, (bytes, type(u''))):
      # We don't want strings to be handled like python collections.
      yield '--%s=%s' % (key, value)
    else:
      # Now we attempt to deal with collections.
      try:
        yield '--%s=%s' % (key, ','.join(itertools.imap(str, value)))
      except TypeError:
        # Default case.
        yield '--%s=%s' % (key, value)


def DocToHelp(doc):
  """Takes a __doc__ string and reformats it as help."""

  # Get rid of starting and ending white space. Using lstrip() or even
  # strip() could drop more than maximum of first line and right space
  # of last line.
  doc = doc.strip()

  # Get rid of all empty lines.
  whitespace_only_line = re.compile('^[ \t]+$', re.M)
  doc = whitespace_only_line.sub('', doc)

  # Cut out common space at line beginnings.
  doc = pep257.trim(doc)

  # Just like this module's comment, comments tend to be aligned somehow.
  # In other words they all start with the same amount of white space.
  # 1) keep double new lines;
  # 2) keep ws after new lines if not empty line;
  # 3) all other new lines shall be changed to a space;
  # Solution: Match new lines between non white space and replace with space.
  doc = re.sub(r'(?<=\S)\n(?=\S)', ' ', doc, flags=re.M)

  return doc
