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
from . import type_names, TYPEDEF_DIR
import logging
logger = logging.getLogger(__name__)

class _NOTGIVEN:
	pass

class TypeDir(EtcDir):
	def __init__(self,*a,**k):
		super().__init__(*a,**k)
		self._type = type_names()['/'.join(self.path[len(TYPEDEF_DIR):-1])]
		self._type.types(self)

class Type:
	"""\
		This is the base class for typing. The attribute `value` holds
		whatever the best representation for Python is (e.g. bool: True/False).
		`amqp_value` is the preferred representation for AMQP, `etcd_value`
		the one for storing in etcd.

		In setup, @meta1 is this type's etcd entry, @meta2 the value's.
		"""
	name = None
	_value = _NOTGIVEN
	vars = {}

	@classmethod
	def types(cls,types):
		pass

	def __init__(self,meta1,meta2,value=_NOTGIVEN):
		self.name = '/'.join(self.meta1.path)
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
	def amqp_value(self):
		"The value as seen by AMQP"
		return self.value
	@amqp_value.setter
	def amqp_value(self,value):
		self.value = value

	@property
	def etcd_value(self):
		"The value as seen by etcd"
		return self.value
	@etcd_value.setter
	def etcd_value(self,value):
		self.value = value

	@property
	def value(self):
		if self._value is _NOTGIVEN:
			raise RuntimeError("You did not set %s" % (self,))
		return self._value
	@value.setter
	def value(self, value):
		value = self.check_var("",value)
		self._value = value

	def check_var(self,var,value):
		"""
			Check whether a variable can be set to that value.
			An empty name denotes the value itself.

			Returns a 'settable' version of the value (converted to float, constrained, whatever).
			"""
		raise CommandError("I don't know about '%s', much less setting it to '%s'" % (var,value))

class StringType(Type):
	name = 'str'

class BoolType(Type):
	name = "bool"
	etcd_class = EtcString
	vars = {'true':'on', 'false':'off'}

	@property
	def value(self):
		return self._value
	@value.setter
	def value(self,value):
		if not isinstance(value,bool):
			raise RuntimeError("%s: need a bool for a bool" % (self.name,))
		self._value = value

	@property
	def etcd_value(self):
		return true if self.value else false
	@etcd_value.setter
	def etcd_value(self,value):
		if value == 'true':
			self.value = True
		elif value == 'false':
			self.value = False
		else:
			raise BadValueError("%s: Dunno what to do with '%s'" % (self.name,value))

	@property
	def amqp_value(self):
		return self['true'] if self.value else self['false']
	@amqp_value.setter
	def amqp_value(self,amqp_value):
		if amqp_value.lower() == self['true'].lower():
			self.value = True
		elif amqp_value.lower() == self['false'].lower():
			self.value = False
		else:
			self.value = bool(int(amqp_value))

class _NumType(Type):
	def check_var(self, var,value):
		if var not in self.vars:
			return super().check_var(var,value)
		try:
			val = self._cls(value)
		except ValueError:
			raise CommandError("%s: need an integer for '%s', not '%s'." % (self.name,var,value))
		if var != 'max':
			if val > self['max']:
				raise CommandError("%s: min %s needs to be smaller than max %s" % (self.name,val,self['max']))
		if var != 'min':
			if val < self['min']:
				raise CommandError("%s: max %s needs to be larger than min %s" % (self.name,val,self['min']))
		# TODO: adapt value to constraints
		return val
	
	@property
	def etcd_value(self):
		return str(self.value)
	@etcd_value.setter
	def etcd_value(self,etcd_value):
		self.value = self._cls(etcd_value)

	@property
	def value(self):
		"""\
			Constrain the value to min/max.
			This is not stupid: the boundaries may have changed.
			"""
		val = self._value
		if val < self['min']:
			logger.warn("%s: Value %s below min %s",self.name,val,self['min'])
			val = self['min']
		elif val > self['max']:
			logger.warn("%s: Value %s above max %s",self.name,val,self['min'])
			val = self['max']
		return val
	@etcd_value.setter
	def value(self,etcd_value):
		val = self._cls(value)
		if val < self['min']:
			logger.warn("%s: Value %s below min %s",self.name,val,self['min'])
			val = self['min']
		elif val > self['max']:
			logger.warn("%s: Value %s above max %s",self.name,val,self['min'])
			val = self['max']
		self._value = val

class IntType(_NumType):
	name = "int"
	etcd_class = EtcInteger
	vars = {'min':0, 'max':100}
	_cls = int

	def types(cls,types):
		types.register('value',cls=EtcInteger)
		types.register('min',cls=EtcInteger)
		types.register('max',cls=EtcInteger)

class FloatType(_NumType):
	name = "float"
	etcd_class = EtcFloat
	_cls = int
	vars = {'min':0, 'max':1}

	def types(cls,types):
		types.register('value',cls=EtcFloat)
		types.register('min',cls=EtcFloat)
		types.register('max',cls=EtcFloat)

class FloatTemperatureType(FloatType):
	name = "float/temperature"
	vars = {'min':-50, 'max':120}

