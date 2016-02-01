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

"""Contains Flag class - information about single command-line flag."""

from functools import total_ordering
from gflags import _helpers
from gflags import argument_parser
from gflags import exceptions


@total_ordering
class Flag(object):
  """Information about a command-line flag.

  'Flag' objects define the following fields:
    .name - the name for this flag;
    .default - the default value for this flag;
    .default_as_str - default value as repr'd string, e.g., "'true'" (or None);
    .value - the most recent parsed value of this flag; set by Parse();
    .help - a help string or None if no help is available;
    .short_name - the single letter alias for this flag (or None);
    .boolean - if 'true', this flag does not accept arguments;
    .present - true if this flag was parsed from command line flags;
    .parser - an ArgumentParser object;
    .serializer - an ArgumentSerializer object;
    .allow_override - the flag may be redefined without raising an error;
    .using_default_value - the flag value has not been set by user;
    .allow_overwrite - the flag may be parsed more than once without raising
                       an error, the last set value will be used.

  The only public method of a 'Flag' object is Parse(), but it is
  typically only called by a 'FlagValues' object.  The Parse() method is
  a thin wrapper around the 'ArgumentParser' Parse() method.  The parsed
  value is saved in .value, and the .present attribute is updated.  If
  this flag was already present, a FlagsError is raised.

  Parse() is also called during __init__ to parse the default value and
  initialize the .value attribute.  This enables other python modules to
  safely use flags even if the __main__ module neglects to parse the
  command line arguments.  The .present attribute is cleared after
  __init__ parsing.  If the default value is set to None, then the
  __init__ parsing step is skipped and the .value attribute is
  initialized to None.

  Note: The default value is also presented to the user in the help
  string, so it is important that it be a legal value for this flag.
  """

  def __init__(self, parser, serializer, name, default, help_string,
               short_name=None, boolean=False, allow_override=False,
               allow_overwrite=True):
    self.name = name

    if not help_string:
      help_string = '(no help available)'

    self.help = help_string
    self.short_name = short_name
    self.boolean = boolean
    self.present = 0
    self.parser = parser
    self.serializer = serializer
    self.allow_override = allow_override
    self.allow_overwrite = allow_overwrite
    self.using_default_value = True
    self.value = None
    self.validators = []

    self.SetDefault(default)

  def __hash__(self):
    return hash(id(self))

  def __eq__(self, other):
    return self is other

  def __lt__(self, other):
    if isinstance(other, Flag):
      return id(self) < id(other)
    return NotImplemented

  def __GetParsedValueAsString(self, value):
    """Get parsed flag value as string."""
    if value is None:
      return None
    if self.serializer:
      return repr(self.serializer.Serialize(value))
    if self.boolean:
      if value:
        return repr('true')
      else:
        return repr('false')
    return repr(_helpers.StrOrUnicode(value))

  def Parse(self, argument):
    """Parse string and set flag value.

    Args:
      argument: String, value to be parsed for flag.
    """
    if self.present and not self.allow_overwrite:
      raise exceptions.IllegalFlagValue(
          'flag --%s=%s: already defined as %s' % (
              self.name, argument, self.value))
    try:
      self.value = self.parser.Parse(argument)
    except ValueError as e:  # Recast ValueError as IllegalFlagValue.
      raise exceptions.IllegalFlagValue(
          'flag --%s=%s: %s' % (self.name, argument, e))
    self.present += 1

  def Unparse(self):
    if self.default is None:
      self.value = None
    else:
      self.present = 0
      self.Parse(self.default)
    self.using_default_value = True
    self.present = 0

  def Serialize(self):
    if self.value is None:
      return ''
    if self.boolean:
      if self.value:
        return '--%s' % self.name
      else:
        return '--no%s' % self.name
    else:
      if not self.serializer:
        raise exceptions.FlagsError(
            'Serializer not present for flag %s' % self.name)
      return '--%s=%s' % (self.name, self.serializer.Serialize(self.value))

  def SetDefault(self, value):
    """Changes the default value (and current value too) for this Flag."""
    # We can't allow a None override because it may end up not being
    # passed to C++ code when we're overriding C++ flags.  So we
    # cowardly bail out until someone fixes the semantics of trying to
    # pass None to a C++ flag.  See swig_flags.Init() for details on
    # this behavior.
    # TODO(olexiy): Users can directly call this method, bypassing all flags
    # validators (we don't have FlagValues here, so we can not check
    # validators).
    # The simplest solution I see is to make this method private.
    # Another approach would be to store reference to the corresponding
    # FlagValues with each flag, but this seems to be an overkill.
    if value is None and self.allow_override:
      raise exceptions.DuplicateFlagCannotPropagateNoneToSwig(self.name)

    self.default = value
    self.Unparse()
    self.default_as_str = self.__GetParsedValueAsString(self.value)

  def Type(self):
    """Get type of flag.

    NOTE: we use strings, and not the types.*Type constants because
    our flags can have more exotic types, e.g., 'comma separated list
    of strings', 'whitespace separated list of strings', etc.

    Returns:
      a string that describes the type of this Flag.
    """
    return self.parser.Type()

  def WriteInfoInXMLFormat(self, outfile, module_name, is_key=False, indent=''):
    """Writes common info about this flag, in XML format.

    This is information that is relevant to all flags (e.g., name,
    meaning, etc.).  If you defined a flag that has some other pieces of
    info, then please override _WriteCustomInfoInXMLFormat.

    Please do NOT override this method.

    Args:
      outfile: File object we write to.
      module_name: A string, the name of the module that defines this flag.
      is_key: A boolean, True iff this flag is key for main module.
      indent: A string that is prepended to each generated line.
    """
    outfile.write(indent + '<flag>\n')
    inner_indent = indent + '  '
    if is_key:
      _helpers.WriteSimpleXMLElement(outfile, 'key', 'yes', inner_indent)
    _helpers.WriteSimpleXMLElement(outfile, 'file', module_name, inner_indent)
    # Print flag features that are relevant for all flags.
    _helpers.WriteSimpleXMLElement(outfile, 'name', self.name, inner_indent)
    if self.short_name:
      _helpers.WriteSimpleXMLElement(outfile, 'short_name', self.short_name,
                                     inner_indent)
    if self.help:
      _helpers.WriteSimpleXMLElement(outfile, 'meaning', self.help,
                                     inner_indent)
    # The default flag value can either be represented as a string like on the
    # command line, or as a Python object.  We serialize this value in the
    # latter case in order to remain consistent.
    if self.serializer and not isinstance(self.default, str):
      if self.default is not None:
        default_serialized = self.serializer.Serialize(self.default)
      else:
        default_serialized = ''
    else:
      default_serialized = self.default
    _helpers.WriteSimpleXMLElement(outfile, 'default', default_serialized,
                                   inner_indent)
    _helpers.WriteSimpleXMLElement(outfile, 'current', self.value, inner_indent)
    _helpers.WriteSimpleXMLElement(outfile, 'type', self.Type(), inner_indent)
    # Print extra flag features this flag may have.
    self._WriteCustomInfoInXMLFormat(outfile, inner_indent)
    outfile.write(indent + '</flag>\n')

  def _WriteCustomInfoInXMLFormat(self, outfile, indent):
    """Writes extra info about this flag, in XML format.

    "Extra" means "not already printed by WriteInfoInXMLFormat above."

    Args:
      outfile: File object we write to.
      indent: A string that is prepended to each generated line.
    """
    # Usually, the parser knows the extra details about the flag, so
    # we just forward the call to it.
    self.parser.WriteCustomInfoInXMLFormat(outfile, indent)


class BooleanFlag(Flag):
  """Basic boolean flag.

  Boolean flags do not take any arguments, and their value is either
  True (1) or False (0).  The false value is specified on the command
  line by prepending the word 'no' to either the long or the short flag
  name.

  For example, if a Boolean flag was created whose long name was
  'update' and whose short name was 'x', then this flag could be
  explicitly unset through either --noupdate or --nox.
  """

  def __init__(self, name, default, help, short_name=None, **args):  # pylint: disable=redefined-builtin
    p = argument_parser.BooleanParser()
    Flag.__init__(self, p, None, name, default, help, short_name, 1, **args)
    if not self.help: self.help = 'a boolean value'


class EnumFlag(Flag):
  """Basic enum flag; its value can be any string from list of enum_values."""

  def __init__(self, name, default, help, enum_values=None,  # pylint: disable=redefined-builtin
               short_name=None, case_sensitive=True, **args):
    enum_values = enum_values or []
    p = argument_parser.EnumParser(enum_values, case_sensitive)
    g = argument_parser.ArgumentSerializer()
    Flag.__init__(self, p, g, name, default, help, short_name, **args)
    if not self.help:
      if case_sensitive:
        self.help = 'an enum string'
      else:
        self.help = 'a case-insensitive enum string'
    self.help = '<%s>: %s' % ('|'.join(enum_values), self.help)

  def _WriteCustomInfoInXMLFormat(self, outfile, indent):
    for enum_value in self.parser.enum_values:
      _helpers.WriteSimpleXMLElement(outfile, 'enum_value', enum_value, indent)


class MultiFlag(Flag):
  """A flag that can appear multiple time on the command-line.

  The value of such a flag is a list that contains the individual values
  from all the appearances of that flag on the command-line.

  See the __doc__ for Flag for most behavior of this class.  Only
  differences in behavior are described here:

    * The default value may be either a single value or a list of values.
      A single value is interpreted as the [value] singleton list.

    * The value of the flag is always a list, even if the option was
      only supplied once, and even if the default value is a single
      value
  """

  def __init__(self, *args, **kwargs):
    Flag.__init__(self, *args, **kwargs)
    self.help += ';\n    repeat this option to specify a list of values'

  def Parse(self, arguments):
    """Parses one or more arguments with the installed parser.

    Args:
      arguments: a single argument or a list of arguments (typically a
        list of default values); a single argument is converted
        internally into a list containing one item.
    """
    if not isinstance(arguments, list):
      # Default value may be a list of values.  Most other arguments
      # will not be, so convert them into a single-item list to make
      # processing simpler below.
      arguments = [arguments]

    if self.present:
      # keep a backup reference to list of previously supplied option values
      values = self.value
    else:
      # "erase" the defaults with an empty list
      values = []

    for item in arguments:
      # have Flag superclass parse argument, overwriting self.value reference
      Flag.Parse(self, item)  # also increments self.present
      values.append(self.value)

    # put list of option values back in the 'value' attribute
    self.value = values

  def Serialize(self):
    if not self.serializer:
      raise exceptions.FlagsError(
          'Serializer not present for flag %s' % self.name)
    if self.value is None:
      return ''

    s = ''

    multi_value = self.value

    for self.value in multi_value:
      if s: s += ' '
      s += Flag.Serialize(self)

    self.value = multi_value

    return s

  def Type(self):
    return 'multi ' + self.parser.Type()

  def _WriteCustomInfoInXMLFormat(self, outfile, indent):
    if hasattr(self.parser, 'enum_values'):
      for enum_value in self.parser.enum_values:
        _helpers.WriteSimpleXMLElement(outfile, 'enum_value',
                                       enum_value, indent)
