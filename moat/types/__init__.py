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

"""List of known Types"""

import os
from ..script.util import objects

import logging
logger = logging.getLogger(__name__)

TYPEDEF_DIR = '/meta/type'
TYPEDEF = ':type'

class _type_names(dict):
	def __getitem__(self,k):
		try:
			return super().__getitem__(k)
		except KeyError:
			if '/' not in k:
				raise
			return self.__getitem__(k[:k.rindex('/')])
_type_names = _type_names()

def types():
	from .base import Type
	return objects(__name__, Type)

def type_names():
	if not _type_names:
		for t in types():
			_type_names[d.name] = t
	return _type_names

def type_types(types):
	from .base import TypeDir
	types.register('**',':type', cls=TypeDir)
