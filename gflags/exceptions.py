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


"""//gflags exceptions."""

import sys

from gflags import _helpers


# TODO(vrusinov): use DISCLAIM_key_flags when it's moved out of __init__.
_helpers.disclaim_module_ids.add(id(sys.modules[__name__]))


class FlagsError(Exception):
  """The base class for all flags errors."""


class DuplicateFlag(FlagsError):
  """Raised if there is a flag naming conflict."""


class CantOpenFlagFileError(FlagsError):
  """Raised if flagfile fails to open: doesn't exist, wrong permissions, etc."""


class DuplicateFlagCannotPropagateNoneToSwig(DuplicateFlag):
  """Special case of DuplicateFlag -- SWIG flag value can't be set to None.

  This can be raised when a duplicate flag is created. Even if allow_override is
  True, we still abort if the new value is None, because it's currently
  impossible to pass None default value back to SWIG. See FlagValues.SetDefault
  for details.
  """


class DuplicateFlagError(DuplicateFlag):
  """A DuplicateFlag whose message cites the conflicting definitions.

  A DuplicateFlagError conveys more information than a DuplicateFlag,
  namely the modules where the conflicting definitions occur. This
  class was created to avoid breaking external modules which depend on
  the existing DuplicateFlags interface.
  """

  def __init__(self, flagname, flag_values, other_flag_values=None):
    """Create a DuplicateFlagError.

    Args:
      flagname: Name of the flag being redefined.
      flag_values: FlagValues object containing the first definition of
          flagname.
      other_flag_values: If this argument is not None, it should be the
          FlagValues object where the second definition of flagname occurs.
          If it is None, we assume that we're being called when attempting
          to create the flag a second time, and we use the module calling
          this one as the source of the second definition.
    """
    self.flagname = flagname
    first_module = flag_values.FindModuleDefiningFlag(
        flagname, default='<unknown>')
    if other_flag_values is None:
      second_module = _helpers.GetCallingModule()
    else:
      second_module = other_flag_values.FindModuleDefiningFlag(
          flagname, default='<unknown>')
    flag_summary = flag_values[self.flagname].help
    msg = ("The flag '%s' is defined twice. First from %s, Second from %s.  "
           "Description from first occurrence: %s") % (
               self.flagname, first_module, second_module, flag_summary)
    DuplicateFlag.__init__(self, msg)


class IllegalFlagValue(FlagsError):
  """The flag command line argument is illegal."""


class UnrecognizedFlag(FlagsError):
  """Raised if a flag is unrecognized."""


# An UnrecognizedFlagError conveys more information than an UnrecognizedFlag.
# Since there are external modules that create DuplicateFlags, the interface to
# DuplicateFlag shouldn't change.  The flagvalue will be assigned the full value
# of the flag and its argument, if any, allowing handling of unrecognized flags
# in an exception handler.
# If flagvalue is the empty string, then this exception is an due to a
# reference to a flag that was not already defined.
class UnrecognizedFlagError(UnrecognizedFlag):

  def __init__(self, flagname, flagvalue='', suggestions=None):
    self.flagname = flagname
    self.flagvalue = flagvalue
    if suggestions:
      tip = '. Did you mean: %s?' % ', '.join(suggestions)
    else:
      tip = ''
    UnrecognizedFlag.__init__(
        self, 'Unknown command line flag \'%s\'%s' % (flagname, tip))


class UnparsedFlagAccessError(FlagsError):
  """Attempt to use flag from unparsed FlagValues."""
