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

from etcd_tree import EtcString,EtcDir,EtcFloat,EtcInteger,EtcValue, ReloadRecursive
from time import time
from moat.util import do_async
from moat.types import TYPEDEF, type_names
from dabroker.unit.rpc import CC_DATA

import logging
logger = logging.getLogger(__name__)

__all__ = ('Device',)

class Typename(EtcString):
	def has_update(self):
		p = self.parent
		if p is None:
			return
		if self._seq is None:
			p._value = None
		else:
			p._set_type(self.value)

class RpcName(EtcString):
	"""Update the parent's rpc name"""
	def has_update(self):
		p = self.parent
		if p is None or not getattr(p.env,'running',False):
			return
		do_async(p._reg_rpc, self.value if self._seq else None)

class AlertName(EtcString):
	"""Update the parent's alert name"""
	def has_update(self):
		p = self.parent
		if p is None or not getattr(p.env,'running',False):
			return
		p._alert_name = (self.value if self._seq else None)

class TypedDir(EtcDir):
	"""\
		A typed value. Typically at …/:dev/input/NAME.

		Its `value` attribute maps to the actual datum.
		"""
	_type = None
	_value = None
	_rpc = None
	_rpc_name = ''
	_alert_name = ''

	@property
	def value(self):
		return self._value.value
	@value.setter
	def value(self,val):
		self._value.value = val

	def _set_type(self, typename):
		if self._type is not None and self._type._type.name == typename:
			return
		self._type = self.env.cmd.root.types.lookup(typename,name=TYPEDEF)

		if 'value' in self:
			if self._value is None:
				self._value = self._type._type(self._type,self)

			self._value.etcd_value = self['value']

	def has_update(self):
		if 'type' not in self:
			self._type = None
			return
		self._set_type(self['type'])

	async def init(self):
		await super().init()
		self.has_update()

	async def _reg_rpc(self,name):
		amqp = self.env.cmd.amqp
		if name is not None and self._rpc_name == name:
			return
		if self._rpc is not None:
			await amqp.unregister_rpc_async(self._rpc)
			self._rpc = None
		if name is not None:
			self._rpc = await amqp.register_rpc_async(name,self._do_rpc, call_conv=CC_DATA)
		self._rpc_name = name

	async def _do_rpc(self,data):
		raise RuntimeError("You forgot to override %s._do_rpc!" % (self.__class__.__name__,))

	async def _updated(self,value, timestamp=None):
		"""A value has been read/written."""
		if timestamp is None:
			timestamp = time()
		elif self.get('timestamp',0) > timestamp:
			# a value from the past gets ignored
			return
		if self._value is None:
			self._value = self._type._type(self._type,self)
		if self._value.value == value:
			await self.set('timestamp',timestamp)
			return
		self._value.value = value
		await self._write_etcd(timestamp)
		await self._write_amqp(timestamp)

	async def reading(self,value, timestamp=None):
		"""A value has been read."""
		await self._updated(value,timestamp)

	async def writing(self,value, timestamp=None):
		"""A value has been written."""
		await self._updated(value,timestamp)

	async def _write_etcd(self,timestamp):
		await self.set('value',self._value.etcd_value)
		await self.set('timestamp',timestamp)

	async def _write_amqp(self,timestamp):
		if not self._alert_name:
			return
		amqp = self.env.cmd.amqp
		await amqp.alert(self._alert_name, _data=self._value.amqp_value)
		
class TypedInputDir(TypedDir):
	async def _do_rpc(self,data):
		val = await self.parent.read(self.name,val)
		await self.reading(val)
		return self._value.amqp_value

class TypedOutputDir(TypedDir):
	async def _do_rpc(self,data):
		val = self._value.from_amqp(data)
		if self._value.value == val:
			return False # already set
		await self.parent.write(self.name,val)
		await self.writing(val)
		return True # OK


TypedDir.register('type',cls=Typename)
TypedDir.register('rpc',cls=RpcName)
TypedDir.register('alert',cls=AlertName)

#class Var(EtcDir):
#	_type = None

#	def __init__(self,*a,**k):
#		super().__init__(*a,**k)


_SOURCES = {'input':TypedInputDir,'output':TypedOutputDir}

class TypesReg(type(EtcDir)):
	"""calls the `types` classmethod after creation"""
	def __init__(cls, name, bases, nmspc):
		super().__init__(name, bases, nmspc)
		cls.types(cls)
	
class BaseDevice(EtcDir, metaclass=TypesReg):
	"""\
		This is the parent class for all MoaT can talk to.

		A Device corresponds to a distinct addressable external entity
		which may have several inputs and/or outputs, or possibly some more
		complex state.

		The device state is always reflected in etcd. Devices do not
		monitor changes in etcd -- use AMQP for that.
		"""

	prefix = "dummy"
	description = "Something that does nothing."

	def __init__(self, *a,**k):
		for attr in _SOURCES:
			if not hasattr(self,attr):
				setattr(self,attr,{})
		super().__init__(*a,**k)

	async def setup(self):
		pass

	@classmethod
	def types(cls, types):
		"""Override to get your subtypes registered with etcd_tree"""
		for s in _SOURCES:
			types.register(s,'*', cls=TypedDir)

	@classmethod
	def dev_paths(cls):
		"""Override to register your device type. Generates
		tuples of prefixes; the device class (instead of ':dev') must be
		the last element."""
		return ()

	async def read(self,what):
		"""Read from the device. This code does NOT update etcd."""
		raise NotImplementedError("I don't know how to read '%s' from %s" % (what,repr(self)))

	async def write(self,what, value):
		"""Write to the device. This code does NOT update etcd."""
		raise NotImplementedError("I don't know how to write '%s' to '%s' of %s" % (value,what,repr(self)))

for attr in _SOURCES:
	BaseDevice.register(attr, cls=TypedDir)

value_types = {
	'float': EtcFloat,
	'int': EtcInteger,
	'str': EtcString,
}

class DeadDevice(BaseDevice):
	"""\
		This device has a broken prefix, the code to use it has been removed,
		or something else is Just Plain Wrong.
		"""
	name = 'dead'
	description = "Code not found"

	@classmethod
	def dev_paths(cls):
		"""Override to register your device type. Generates
		tuples of prefixes; the device class (instead of ':dev') must be
		the last element."""
		yield '**',cls

class Device(BaseDevice):
	"""\
		This is the superclass for devices that actually work
		(or are supposed to work). Use this instead of BaseDevice
		unless you have a very good reason not to.

		Specifically, DeadDevice does not implement any AMQP hooks.
		"""
	prefix = None
	description = "Override me"

	@classmethod
	async def this_class(cls, pre,recursive):
		if not recursive:
			raise ReloadRecursive
		return (await super().this_class(pre=pre,recursive=recursive))

	@classmethod
	def types(cls, types):
		"""\
			Register value types with etcd_tree.
			Override to add your own categories; add to your
			input{}/output{} for atomic values"""

		for d in _SOURCES:
			types.register(d,'*','timestamp', cls=EtcFloat)
			types.register(d,'*','created', cls=EtcFloat)
			for k,v in getattr(cls,d,{}).items():
				v = value_types.get(v,EtcValue)
				types.register(d,k,'value', cls=v)

	async def setup(self):
		"""\
			Create this device's data in etcd.

			This code must be idempotent and nondestructive.

			The default implementation creates variables for all types
			mentioned in self.input and .output.
			"""
		await super().setup()
		for d in _SOURCES:
			missing = {}
			src = self.get(d,{})
			for k,v in getattr(self,d,{}).items():
				if 'type' in src.get(k,{}):
					continue
				missing[k] = {'type':v,'created':time()}
			if missing:
				await self.set(d,missing)
				# Note that this does not delete anything not mentioned

	async def reading(self,what,value, timestamp=None):
		"""We have an input value"""
		await self['input'][what].reading(value, timestamp)

	async def writing(self,what,value, timestamp=None):
		"""We have an output value"""
		await self['output'][what].writing(value,timestamp)

