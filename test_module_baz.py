#!/usr/bin/python2.4
#
# Copyright 2010 Google Inc. All Rights Reserved.

"""Auxiliary module for testing flags.py.

The purpose of this module is to test the behavior of flags that are defined
before main() executes.
"""


__author__ = 'mikecurtis@google.com (Michael Bennett Curtis)'

import gflags as flags

FLAGS = flags.FLAGS

flags.DEFINE_boolean('tmod_baz_x', True, 'Boolean flag.')
