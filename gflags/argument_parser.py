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


"""Contains base classes used to parse and convert arguments."""

import cStringIO
import csv
import string


from gflags import _helpers


class _ArgumentParserCache(type):
  """Metaclass used to cache and share argument parsers among flags."""

  _instances = {}

  def __call__(cls, *args, **kwargs):
    """Returns an instance of the argument parser cls.

    This method overrides behavior of the __new__ methods in
    all subclasses of ArgumentParser (inclusive). If an instance
    for cls with the same set of arguments exists, this instance is
    returned, otherwise a new instance is created.

    If any keyword arguments are defined, or the values in args
    are not hashable, this method always returns a new instance of
    cls.

    Args:
      *args: Positional initializer arguments.
      **kwargs: Initializer keyword arguments.

    Returns:
      An instance of cls, shared or new.
    """
    if kwargs:
      return type.__call__(cls, *args, **kwargs)
    else:
      instances = cls._instances
      key = (cls,) + tuple(args)
      try:
        return instances[key]
      except KeyError:
        # No cache entry for key exists, create a new one.
        return instances.setdefault(key, type.__call__(cls, *args))
      except TypeError:
        # An object in args cannot be hashed, always return
        # a new instance.
        return type.__call__(cls, *args)


class ArgumentParser(object):
  """Base class used to parse and convert arguments.

  The Parse() method checks to make sure that the string argument is a
  legal value and convert it to a native type.  If the value cannot be
  converted, it should throw a 'ValueError' exception with a human
  readable explanation of why the value is illegal.

  Subclasses should also define a syntactic_help string which may be
  presented to the user to describe the form of the legal values.

  Argument parser classes must be stateless, since instances are cached
  and shared between flags. Initializer arguments are allowed, but all
  member variables must be derived from initializer arguments only.
  """
  __metaclass__ = _ArgumentParserCache

  syntactic_help = ''

  def Parse(self, argument):
    """Default implementation: always returns its argument unmodified."""
    return argument

  def Type(self):
    return 'string'

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    pass


class ArgumentSerializer(object):
  """Base class for generating string representations of a flag value."""

  def Serialize(self, value):
    return _helpers.StrOrUnicode(value)


class NumericParser(ArgumentParser):
  """Parser of numeric values.

  Parsed value may be bounded to a given upper and lower bound.
  """

  def IsOutsideBounds(self, val):
    return ((self.lower_bound is not None and val < self.lower_bound) or
            (self.upper_bound is not None and val > self.upper_bound))

  def Parse(self, argument):
    val = self.Convert(argument)
    if self.IsOutsideBounds(val):
      raise ValueError('%s is not %s' % (val, self.syntactic_help))
    return val

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    if self.lower_bound is not None:
      _helpers.WriteSimpleXMLElement(outfile, 'lower_bound', self.lower_bound,
                                     indent)
    if self.upper_bound is not None:
      _helpers.WriteSimpleXMLElement(outfile, 'upper_bound', self.upper_bound,
                                     indent)

  def Convert(self, argument):
    """Default implementation: always returns its argument unmodified."""
    return argument


class FloatParser(NumericParser):
  """Parser of floating point values.

  Parsed value may be bounded to a given upper and lower bound.
  """
  number_article = 'a'
  number_name = 'number'
  syntactic_help = ' '.join((number_article, number_name))

  def __init__(self, lower_bound=None, upper_bound=None):
    super(FloatParser, self).__init__()
    self.lower_bound = lower_bound
    self.upper_bound = upper_bound
    sh = self.syntactic_help
    if lower_bound is not None and upper_bound is not None:
      sh = ('%s in the range [%s, %s]' % (sh, lower_bound, upper_bound))
    elif lower_bound == 0:
      sh = 'a non-negative %s' % self.number_name
    elif upper_bound == 0:
      sh = 'a non-positive %s' % self.number_name
    elif upper_bound is not None:
      sh = '%s <= %s' % (self.number_name, upper_bound)
    elif lower_bound is not None:
      sh = '%s >= %s' % (self.number_name, lower_bound)
    self.syntactic_help = sh

  def Convert(self, argument):
    """Converts argument to a float; raises ValueError on errors."""
    return float(argument)

  def Type(self):
    return 'float'
# End of FloatParser


class IntegerParser(NumericParser):
  """Parser of an integer value.

  Parsed value may be bounded to a given upper and lower bound.
  """
  number_article = 'an'
  number_name = 'integer'
  syntactic_help = ' '.join((number_article, number_name))

  def __init__(self, lower_bound=None, upper_bound=None):
    super(IntegerParser, self).__init__()
    self.lower_bound = lower_bound
    self.upper_bound = upper_bound
    sh = self.syntactic_help
    if lower_bound is not None and upper_bound is not None:
      sh = ('%s in the range [%s, %s]' % (sh, lower_bound, upper_bound))
    elif lower_bound == 1:
      sh = 'a positive %s' % self.number_name
    elif upper_bound == -1:
      sh = 'a negative %s' % self.number_name
    elif lower_bound == 0:
      sh = 'a non-negative %s' % self.number_name
    elif upper_bound == 0:
      sh = 'a non-positive %s' % self.number_name
    elif upper_bound is not None:
      sh = '%s <= %s' % (self.number_name, upper_bound)
    elif lower_bound is not None:
      sh = '%s >= %s' % (self.number_name, lower_bound)
    self.syntactic_help = sh

  def Convert(self, argument):
    if type(argument) == str:
      base = 10
      if len(argument) > 2 and argument[0] == '0':
        if argument[1] == 'o':
          base = 8
        elif argument[1] == 'x':
          base = 16
      return int(argument, base)
    else:
      return int(argument)

  def Type(self):
    return 'int'


class BooleanParser(ArgumentParser):
  """Parser of boolean values."""

  def Convert(self, argument):
    """Converts the argument to a boolean; raise ValueError on errors."""
    if type(argument) == str:
      if argument.lower() in ['true', 't', '1']:
        return True
      elif argument.lower() in ['false', 'f', '0']:
        return False

    bool_argument = bool(argument)
    if argument == bool_argument:
      # The argument is a valid boolean (True, False, 0, or 1), and not just
      # something that always converts to bool (list, string, int, etc.).
      return bool_argument

    raise ValueError('Non-boolean argument to boolean flag', argument)

  def Parse(self, argument):
    val = self.Convert(argument)
    return val

  def Type(self):
    return 'bool'


class EnumParser(ArgumentParser):
  """Parser of a string enum value (a string value from a given set).

  If enum_values (see below) is not specified, any string is allowed.
  """

  def __init__(self, enum_values=None, case_sensitive=True):
    """Initialize EnumParser.

    Args:
      enum_values: Array of values in the enum.
      case_sensitive: Whether or not the enum is to be case-sensitive.
    """
    super(EnumParser, self).__init__()
    self.enum_values = enum_values
    self.case_sensitive = case_sensitive

  def Parse(self, argument):
    """Determine validity of argument and return the correct element of enum.

    If self.enum_values is empty, then all arguments are valid and argument
    will be returned.

    Otherwise, if argument matches an element in enum, then the first
    matching element will be returned.

    Args:
      argument: The supplied flag value.

    Returns:
      The matching element from enum_values, or argument if enum_values is
      empty.

    Raises:
      ValueError: enum_values was non-empty, but argument didn't match
        anything in enum.
    """
    if not self.enum_values:
      return argument
    elif self.case_sensitive:
      if argument not in self.enum_values:
        raise ValueError('value should be one of <%s>' %
                         '|'.join(self.enum_values))
      else:
        return argument
    else:
      if argument.upper() not in [value.upper() for value in self.enum_values]:
        raise ValueError('value should be one of <%s>' %
                         '|'.join(self.enum_values))
      else:
        return [value for value in self.enum_values
                if value.upper() == argument.upper()][0]

  def Type(self):
    return 'string enum'


class ListSerializer(ArgumentSerializer):

  def __init__(self, list_sep):
    self.list_sep = list_sep

  def Serialize(self, value):
    return self.list_sep.join([_helpers.StrOrUnicode(x) for x in value])


class CsvListSerializer(ArgumentSerializer):

  def __init__(self, list_sep):
    self.list_sep = list_sep

  def Serialize(self, value):
    """Serialize a list as a string, if possible, or as a unicode string."""
    output = cStringIO.StringIO()
    writer = csv.writer(output)

    # csv.writer doesn't accept unicode, so we convert to UTF-8.
    encoded_value = [unicode(x).encode('utf-8') for x in value]
    writer.writerow(encoded_value)

    # We need the returned value to be pure ascii or Unicodes so that
    # when the xml help is generated they are usefully encodable.
    return _helpers.StrOrUnicode(output.getvalue().strip().decode('utf-8'))


class BaseListParser(ArgumentParser):
  """Base class for a parser of lists of strings.

  To extend, inherit from this class; from the subclass __init__, call

    BaseListParser.__init__(self, token, name)

  where token is a character used to tokenize, and name is a description
  of the separator.
  """

  def __init__(self, token=None, name=None):
    assert name
    super(BaseListParser, self).__init__()
    self._token = token
    self._name = name
    self.syntactic_help = 'a %s separated list' % self._name

  def Parse(self, argument):
    if isinstance(argument, list):
      return argument
    elif not argument:
      return []
    else:
      return [s.strip() for s in argument.split(self._token)]

  def Type(self):
    return '%s separated list of strings' % self._name


class ListParser(BaseListParser):
  """Parser for a comma-separated list of strings."""

  def __init__(self):
    BaseListParser.__init__(self, ',', 'comma')

  def Parse(self, argument):
    """Override to support full CSV syntax."""
    if isinstance(argument, list):
      return argument
    elif not argument:
      return []
    else:
      try:
        return [s.strip() for s in list(csv.reader([argument], strict=True))[0]]
      except csv.Error as e:
        # Provide a helpful report for case like
        #   --listflag="$(printf 'hello,\nworld')"
        # IOW, list flag values containing naked newlines.  This error
        # was previously "reported" by allowing csv.Error to
        # propagate.
        raise ValueError('Unable to parse the value %r as a %s: %s'
                         % (argument, self.Type(), e))

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    BaseListParser.WriteCustomInfoInXMLFormat(self, outfile, indent)
    _helpers.WriteSimpleXMLElement(outfile, 'list_separator', repr(','), indent)


class WhitespaceSeparatedListParser(BaseListParser):
  """Parser for a whitespace-separated list of strings."""

  def __init__(self, comma_compat=False):
    """Initializer.

    Args:
      comma_compat: bool - Whether to support comma as an additional separator.
          If false then only whitespace is supported.  This is intended only for
          backwards compatibility with flags that used to be comma-separated.
    """
    self._comma_compat = comma_compat
    name = 'whitespace or comma' if self._comma_compat else 'whitespace'
    BaseListParser.__init__(self, None, name)

  def Parse(self, argument):
    """Override to support comma compatibility."""
    if isinstance(argument, list):
      return argument
    elif not argument:
      return []
    else:
      if self._comma_compat:
        argument = argument.replace(',', ' ')
      return argument.split()

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    BaseListParser.WriteCustomInfoInXMLFormat(self, outfile, indent)
    separators = list(string.whitespace)
    if self._comma_compat:
      separators.append(',')
    separators.sort()
    for sep_char in separators:
      _helpers.WriteSimpleXMLElement(outfile, 'list_separator', repr(sep_char),
                                     indent)
