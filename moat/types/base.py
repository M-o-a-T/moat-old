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

from etcd_tree.node import EtcString,EtcInteger,EtcFloat, EtcDir
from etcd_tree.etcd import EtcTypes
from . import type_names, TYPEDEF_LEN
import logging
logger = logging.getLogger(__name__)

class _NOTGIVEN:
	pass

class TypeDir(EtcDir):
	def __init__(self,*a,**k):
		super().__init__(*a,**k)
		self._type = type_names()['/'.join(self.path[TYPEDEF_LEN:-1])]
		self._type.types(self)

class Type:
	"""\
		This is the base class for typing. The attribute `value` holds
		whatever the best representation for Python is (e.g. bool: True/False).
		`bus_value` is the preferred representation for AMQP, `etcd_value`
		the one for storing in etcd.

		In setup, @meta1 is this type's etcd entry, @meta2 the value's.
		"""
	name = None
	value = _NOTGIVEN
	vars = {}

	@classmethod
	def types(cls,types):
		pass

	def __init__(self,meta1,meta2,value=_NOTGIVEN):
		self.meta1 = meta1
		self.meta2 = meta2

		if value is not _NOTGIVEN:
			self.etcd_value = value

	def __getitem__(self,key):
		try:
			return self.meta2[key]
		except KeyError:
			try:
				return self.meta1[key]
			except KeyError:
				return type(self).vars[key]

	@property
	def bus_value(self):
		return self.value
	@bus_value.setter
	def bus_value(self,bus_value):
		self.value = bus_value

	@property
	def etcd_value(self):
		return self.value
	@etcd_value.setter
	def etcd_value(self,etcd_value):
		self.value = etcd_value

	def check_var(self,var,value):
		"""Check whether a variable can be set to that value"""
		raise CommandError("I don't know about '%s', much less setting it to '%s'" % (var,value))

class StringType(Type):
	name = 'str'

class BoolType(Type):
	name = "bool"
	etcd_class = EtcString
	vars = {'true':'on', 'false':'off'}

	@property
	def bus_value(self):
		return self['true'] if self.value else self['false']
	@bus_value.setter
	def bus_value(self,bus_value):
		if bus_value.lower() == self['true'].lower():
			self.value = True
		elif bus_value.lower() == self['false'].lower():
			self.value = False
		else:
			self.value = bool(int(bus_value))

class _NumType(Type):
	def check_var(self, var,value):
		if var not in self.vars:
			return super().check_var(var,value)
		try:
			val = self._cls(value)
		except ValueError:
			raise CommandError("need an integer for '%s', not '%s'." % (var,value))
		if var == 'min':
			if var > self['max']:
				raise CommandError("min %s needs to be smaller than max %s" % (val,self['max']))
		elif var == 'max':
			if var < self['min']:
				raise CommandError("max %s needs to be larger than min %s" % (val,self['min']))
	
	@property
	def etcd_value(self):
		return str(self.value)
	@etcd_value.setter
	def etcd_value(self,etcd_value):
		self.value = self._cls(etcd_value)

	@property
	def etcd_value(self):
		return str(self.value)
	@etcd_value.setter
	def etcd_value(self,etcd_value):
		val = self._cls(etcd_value)
		if val < self['min']:
			val = self['min']
		elif val > self['max']:
			val = self['max']
		self.value = self._cls(etcd_value)

class IntType(_NumType):
	name = "int"
	etcd_class = EtcInteger
	vars = {'min':0, 'max':100}
	_cls = int

	@classmethod
	def types(cls,types):
		types.register('min',cls=EtcFloat)
		types.register('max',cls=EtcFloat)

class FloatType(_NumType):
	name = "float"
	etcd_class = EtcFloat
	_cls = int
	vars = {'min':0, 'max':1}

	@classmethod
	def types(cls,types):
		types.register('min',cls=EtcFloat)
		types.register('max',cls=EtcFloat)

class FloatTemperatureType(FloatType):
	name = "float/temperature"
	vars = {'min':-50, 'max':120}

