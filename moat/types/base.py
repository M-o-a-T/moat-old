# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2016 by Matthias Urlichs <matthias@urlichs.de>,
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

TRUE = {'true','True','1','on','On','ON',1,True}
FALSE = {'false','False','0','off','Off','OFF',0,False}

class _NOTGIVEN:
	pass

class BadValueError(RuntimeError):
    """The input doesn't match the expected values"""
    def __init__(self, inp,val):
        self.inp = inp
        self.val = val
    def __str__(self):
        return "BadValue: read %s: bad value for %s" % (self.val,self.inp)

class TypeDir(EtcDir):
	"""A class linking a type to its etcd entry"""
	def __init__(self,*a,**k):
		super().__init__(*a,**k)
		self._type = type_names()['/'.join(self.path[len(TYPEDEF_DIR):-1])]
		self._type.types(self)
TypeDir.register('timestamp',cls=EtcFloat)
TypeDir.register('created',cls=EtcFloat)

class Type:
	"""\
		This is the (abstract) base class for typing; it holds one typed value.

		The attribute `value` contains whatever the best representation for
		Python is (e.g. bool: True/False).
		`amqp_value` is the preferred representation for AMQP, `etcd_value`
		the one for storing in etcd.
		"""
	name = None
	_value = _NOTGIVEN
	vars = {}
	default = None

	@classmethod
	def types(cls,types):
		pass

	def __init__(self,meta1=None,meta2=None,value=_NOTGIVEN):
		"""\
			@meta1 is the type's etcd entry, @meta2 the value's.
			Both may be zero if all you need is to convert some value.
			"""
		if meta1 is not None:
			self.name = '/'.join(meta1.path)
			self.meta1 = meta1
		if meta2 is not None:
			self.meta2 = meta2

		if value is not _NOTGIVEN:
			self.etcd_value = value

	def __getitem__(self,key):
		try:
			return self.meta2[key]
		except (AttributeError,KeyError):
			try:
				return self.meta1[key]
			except (AttributeError,KeyError):
				return type(self).vars[key]

	@property
	def amqp_value(self):
		"The value as seen by AMQP"
		return self.to_amqp(self.value)
	@amqp_value.setter
	def amqp_value(self,value):
		self.value = self.from_amqp(value)

	def from_amqp(self,value):
		return value
	def to_amqp(self,value):
		return value

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
		raise ValueError("I don't know about '%s', much less setting it to '%s'" % (var,value))

class StringType(Type):
	name = 'str'
	etcd_class = EtcString
	default = ""

class PathType(StringType):
	name = 'str/path'
	default = "/"

	@property
	def etcd_value(self):
		if self.value:
			return '/'.join(self.value)
		else:
			return '/'
	@etcd_value.setter
	def etcd_value(self,value):
		if value == '/':
			self.value == ()
		else:
			self.value = tuple(value.split('/'))
			assert '' not in self.value

class HostType(StringType):
	name = 'str/hostname'
	default = "localhost"

class ObjType(StringType):
	name = 'str/obj'
	default = None

	@property
	def value(self):
		return import_string(self._value)
	@value.setter
	def value(self,value):
		self._value = value.__module__+'.'+value.__name__

class BoolType(Type):
	name = "bool"
	default = False

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
		return self.value
	@etcd_value.setter
	def etcd_value(self,value):
		if value in TRUE:
			self.value = True
		elif value in FALSE:
			self.value = False
		else:
			raise BadValueError("%s: Dunno what to do with '%s'" % (self.name,value))

	def to_amqp(self, value):
		return self['true'] if value else self['false']

	def from_amqp(self,value):
		if value in TRUE:
			return True
		elif value in FALSE:
			return False
		elif value == self['true']:
			return True
		elif value == self['false']:
			return False
		elif value.lower() == self['true'].lower():
			return True
		elif value.lower() == self['false'].lower():
			return False
		else:
			raise ValueError(value)

class _NumType(Type):
	default = 0

	def check_var(self, var,value):
		try:
			val = self._cls(value)
		except ValueError:
			raise CommandError("%s: need an integer for '%s', not '%s'." % (self.name,var,value))
		if var != 'max':
			try:
				if val > self['max']:
					raise CommandError("%s: min %s needs to be smaller than max %s" % (self.name,val,self['max']))
			except KeyError:
				pass
		if var != 'min':
			try:
				if val < self['min']:
					raise CommandError("%s: max %s needs to be larger than min %s" % (self.name,val,self['min']))
			except KeyError:
				pass
		# TODO: adapt value to constraints
		return val
	
	@property
	def etcd_value(self):
		return self.value
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
		if val is not _NOTGIVEN:
			try:
				if val < self['min']:
					logger.warn("%s: Value %s below min %s",self.name,val,self['min'])
					val = self['min']
			except KeyError:
				pass
			try:
				if val > self['max']:
					logger.warn("%s: Value %s above max %s",self.name,val,self['min'])
					val = self['max']
			except KeyError:
				pass
		return val
	@value.setter
	def value(self,value):
		val = self._cls(value)
		try:
			if val < self['min']:
				logger.warn("%s: Value %s below min %s",self.name,val,self['min'])
				val = self['min']
		except KeyError:
			pass
		try:
			if val > self['max']:
				logger.warn("%s: Value %s above max %s",self.name,val,self['min'])
				val = self['max']
		except KeyError:
			pass
		self._value = val

	def from_amqp(self, value):
		return self.check_var('',value)

class IntType(_NumType):
	name = "int"
	etcd_class = EtcInteger
	#vars = {'min':0, 'max':100}
	_cls = int

	@classmethod
	def types(cls,types):
		types.register('value',cls=EtcInteger)
		types.register('min',cls=EtcInteger)
		types.register('max',cls=EtcInteger)

class IntPortType(IntType):
	name = "int/port"
	vars = {'min':1, 'max':65534}

class IntPercentType(IntType):
	name = "int/percent"
	vars = {'min':0, 'max':100}

class FloatType(_NumType):
	name = "float"
	etcd_class = EtcFloat
	_cls = float

	@classmethod
	def types(cls,types):
		types.register('value',cls=EtcFloat)
		types.register('min',cls=EtcFloat)
		types.register('max',cls=EtcFloat)

class FloatTimeType(FloatType):
	name = "float/time"
	vars = {'min':0.01}

class FloatPercentType(FloatType):
	name = "float/percent"
	vars = {'min':0, 'max':1}

class FloatTemperatureType(FloatType):
	name = "float/temperature"
	vars = {'min':-50, 'max':120}

