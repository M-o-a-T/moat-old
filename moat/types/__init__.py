# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2015 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
##
##  This program is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License (included; see the file LICENSE)
##  for more details.
##
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

"""\
This package implements the high-level Type object in MoaT.

Types translate between some sensible internal value and various external
representations. For instance, interally a switch is on or off (True or
False) while on 1wire the bit is 1 or 0, on an MQTT bus it's "on" or "off"
(or "ON and "OFF"), in etcd it's 'true' or 'false', etc.

The internal value shall be the one that makes the most sense to the
computer. For instance, intensity of a dimmable light is between zero and
one. It's the GUI's responsibility to map "float/percentage" to something
nicer.

"""

import os
from ..script.util import objects
from etcd_tree import EtcTypes

import logging
logger = logging.getLogger(__name__)

MODULE_DIR = ('meta','module')

# Type definitions declare data types and bounds for the rest of MoaT.
TYPEDEF_DIR = ('meta','type')
TYPEDEF = ':type'

class _type_names(dict):
	def __getitem__(self,k):
		while True:
			try:
				return super().__getitem__(k)
			except KeyError:
				if '/' not in k:
					from .base import Type
					return Type
			k = k[:k.rindex('/')]
_type_names = _type_names()

def types():
	"""Generator for all types known to MoaT. This accesses the code."""
	from .base import Type
	return objects(__name__, Type, filter=lambda x:x.name is not None)

def type_names():
	"""Creates a dict which maps type names to its moat.types.*.Type object."""
	if not _type_names:
		for t in types():
			_type_names[t.name] = t
	return _type_names

def setup_meta_types(types):
	"""Teach an EtcTypes object about MoaT types"""
	from .base import TypeDir
	types.step(TYPEDEF_DIR).register('**',TYPEDEF, cls=TypeDir)

