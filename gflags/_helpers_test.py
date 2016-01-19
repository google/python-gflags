#!/usr/bin/env python
# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Unittest for helpers module."""

import unittest

from gflags import _helpers


class FlagSuggestionTest(unittest.TestCase):

  def setUp(self):
    self.longopts = [
        'fsplit-ivs-in-unroller=',
        'fsplit-wide-types=',
        'fstack-protector=',
        'fstack-protector-all=',
        'fstrict-aliasing=',
        'fstrict-overflow=',
        'fthread-jumps=',
        'ftracer',
        'ftree-bit-ccp',
        'ftree-builtin-call-dce',
        'ftree-ccp',
        'ftree-ch']

  def testDamerauLevenshteinId(self):
    self.assertEqual(0, _helpers._DamerauLevenshtein('asdf', 'asdf'))

  def testDamerauLevenshteinEmpty(self):
    self.assertEqual(5, _helpers._DamerauLevenshtein('', 'kites'))
    self.assertEqual(6, _helpers._DamerauLevenshtein('kitten', ''))

  def testDamerauLevenshteinCommutative(self):
    self.assertEqual(2, _helpers._DamerauLevenshtein('kitten', 'kites'))
    self.assertEqual(2, _helpers._DamerauLevenshtein('kites', 'kitten'))

  def testDamerauLevenshteinTransposition(self):
    self.assertEqual(1, _helpers._DamerauLevenshtein('kitten', 'ktiten'))

  def testMispelledSuggestions(self):
    suggestions = _helpers.GetFlagSuggestions('fstack_protector_all',
                                              self.longopts)
    self.assertEqual(['fstack-protector-all'], suggestions)

  def testAmbiguousPrefixSuggestion(self):
    suggestions = _helpers.GetFlagSuggestions('fstack', self.longopts)
    self.assertEqual(['fstack-protector', 'fstack-protector-all'], suggestions)

  def testMisspelledAmbiguousPrefixSuggestion(self):
    suggestions = _helpers.GetFlagSuggestions('stack', self.longopts)
    self.assertEqual(['fstack-protector', 'fstack-protector-all'], suggestions)

  def testCrazySuggestion(self):
    suggestions = _helpers.GetFlagSuggestions('asdfasdgasdfa', self.longopts)
    self.assertEqual([], suggestions)


def main():
  unittest.main()


if __name__ == '__main__':
  main()
