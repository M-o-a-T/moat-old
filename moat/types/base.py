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

from etcd_tree.node import mtString,mtInteger,mtFloat
import logging
logger = logging.getLogger(__name__)

class _NOTGIVEN:
	pass

class Type:
	"""\
		This is the base class for typing. The attribute `value` holds
		whatever the best representation for Python is (e.g. bool: True/False).
		`bus_value` is the preferred representation for AMQP, `etc_value`
		the one for storing in etcd.

		In setup, @meta is this type's etcd entry.
		"""
	name = None
	value = _NOTGIVEN
	vars = {}

	def __init__(self,meta,value=_NOTGIVEN,wire=False):
		self.meta = meta

		if value is not _NOTGIVEN:
			if wire:
				self.bus_value = value
			else:
				self.int_value = value

	@property
	def bus_value(self):
		return self.value
	@bus_value.setter
	def bus_value(self,bus_value):
		self.value = bus_value

	@property
	def etc_value(self):
		return self.value
	@etc_value.setter
	def etc_value(self,etc_value):
		self.value = etc_value
	

class BoolType(Type):
	name = "bool"
	etc_class = mtString
	vars = {'true':'on', 'false':'off'}


class IntType(Type):
	name = "int"
	etc_class = mtInteger
	vars = {'min':0, 'max':100}

class FloatType(Type):
	name = "float"
	etc_class = mtFloat
	vars = {'min':0, 'max':1}

class FloatTempType(FloatType):
	name = "float/temperature"
	vars = {'min':-50, 'max':120}

