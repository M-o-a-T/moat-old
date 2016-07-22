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

from etcd_tree import EtcString,EtcDir,EtcFloat,EtcInteger,EtcValue, ReloadRecursive
import asyncio
import aio_etcd as etcd
from time import time
from weakref import ref

from moat.util import do_async
from moat.types import TYPEDEF_DIR,TYPEDEF, type_names
from moat.types.managed import ManagedEtcThing,ManagedEtcDir
from qbroker.unit import CC_DATA
from . import devices, DEV

import logging
logger = logging.getLogger(__name__)

__all__ = ('Device',)

def setup_dev_types(types):
	"""Register types for all devices."""
	for dev in devices():
		t = types.step(dev.prefix)
		for p in dev.dev_paths():
			t.step(p[:-1]).register(DEV, cls=p[-1])
	types.register('**',DEV, cls=DeadDevice)

class MoatDevices(EtcDir):
	"""singleton for etcd /device"""
	async def init(self):
		setup_dev_types(self)

		await super().init()

class Typename(EtcString):
	def has_update(self):
		p = self.parent
		if p is None:
			return
		if self.is_new is None:
			p._value = None
		else:
			p._set_type(self.value)

class RpcName(EtcString):
	"""Update the parent's rpc name"""
	def has_update(self):
		p = self.parent
		if p is None:
			return
		m = p.manager
		if m is None:
			return
		m.call_async(p._reg_rpc, self.value if self.is_new is not None else None)

class AlertName(EtcString):
	"""Update the parent's alert name"""
	def has_update(self):
		p = self.parent
		if p is None:
			return
		p._alert_name = (self.value if self.is_new is not None else None)

class TypedDir(ManagedEtcThing,EtcDir):
	"""\
		A typed value. Typically at …/:dev/input/NAME.

		Its `value` attribute maps to the actual datum.
		"""
	_type = None
	_value = None
	_rpc = None
	_rpc_name = ''
	_alert_name = ''
	_device = None

	@property
	def value(self):
		return self._value.value
	@value.setter
	def value(self,val):
		self._value.value = val

	@property
	def device(self):
		"""Returns 'my' device."""
		if self._device is not None:
			return self._device()
		p = self.parent
		while p is not None:
			if isinstance(p,BaseDevice):
				self._device = ref(p)
				return p
			p = p.parent
		return None

	def _set_type(self, typename):
		if self._type is not None and self._type._type.name == typename:
			return
		self._type = self.root.lookup(TYPEDEF_DIR).lookup(typename,name=TYPEDEF)

		if self._value is None:
			self._value = self._type._type(self._type,self)

		if 'value' in self:
			self._value.etcd_value = self['value']

	def has_update(self):
		if 'type' not in self:
			self._type = None
			return
		self._set_type(self['type'])

	async def init(self):
		await super().init()
		self.has_update()

	## Manager registration

	async def manager_present(self, mgr):
		n = self.get('rpc',None)
		if n is not None:
			await self._reg_rpc(n)

	def manager_gone(self):
		self._rpc_name = None

	async def _reg_rpc(self,name):
		m = self.manager
		if m is None:
			return
		amqp = m.amqp
		if name is not None and self._rpc_name == name:
			return
		if self._rpc is not None:
			await amqp.unregister_rpc_async(self._rpc)
			self._rpc = None
		if name is not None:
			logger.info("REG @%s %s %s %s %s",id(amqp),self,id(self),self.root,id(self.root))
			self._rpc = await amqp.register_rpc_async(name,self.do_rpc, call_conv=CC_DATA)
		self._rpc_name = name

	async def do_rpc(self,data):
		"""\
			RPC call. Override to actually do something.
			"""
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

		while True:
			if self.get('timestamp',0) > timestamp:
				logger.info("Skipping update: %s %s %s",self,self['timestamp'],timestamp)
				return
			try:
				if self._value.value == value:
					await self.set('timestamp',timestamp)
				else:
					self._value.value = value
					await self._write_etcd(timestamp)
				await self._write_amqp(timestamp)
			except asyncio.CancelledError as exc:
				raise
			except etcd.EtcdCompareFailed as exc:
				logger.info("Retrying update: %s %s",self,str(exc))
				await self.wait(exc.payload['index'])
			except Exception as exc:
				logger.exception("Ouch")
				raise
			else:
				break

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
		m = await self.manager_async
		amqp = m.amqp
		await amqp.alert(self._alert_name, _data=self._value.amqp_value)

class TypedInputDir(TypedDir):
	async def do_rpc(self,data):
		val = await self.parent.parent.read(self.name,val)
		await self.reading(val)
		return self._value.amqp_value

class TypedOutputDir(TypedDir):
	async def do_rpc(self,data):
		val = self._value.from_amqp(data)
		if self._value.value == val:
			return False # already set
		await self.parent.parent.write(self.name,val)
		await self.writing(val)
		return True # OK

TypedDir.register('type',cls=Typename)
TypedDir.register('rpc',cls=RpcName)
TypedDir.register('alert',cls=AlertName)

TypedDir.register('created',cls=EtcFloat)
TypedDir.register('timestamp',cls=EtcFloat)

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
		This is the parent class for all things MoaT can talk to.

		A Device corresponds to a distinct addressable external entity
		which may have several inputs and/or outputs, or possibly some more
		complex state.

		The device state is always reflected in etcd. Devices do not
		monitor changes in etcd -- use AMQP for that.
		"""

	prefix = "dummy"
	description = "Something that does nothing."
	_mgr = None

	def __init__(self, *a,**k):
		for attr in _SOURCES:
			if not hasattr(self,attr):
				setattr(self,attr,{})
		super().__init__(*a,**k)

	async def setup(self):
		pass

	async def set_managed(self, mgr):
		"""Async manager callback after adding a manager"""
		pass

	async def set_unmanaged(self):
		"""Async manager callback after killing a manager"""
		pass

	def has_update(self):
		super().has_update()
		m = self.manager
		if m is not None:
			if self.is_new:
				m.add_device(self)
			elif self.is_new is None:
				m.drop_device(self)

	@classmethod
	def types(cls, types):
		"""Override to get your subtypes registered with etcd_tree"""
		for s,t in _SOURCES.items():
			types.register(s,'*', cls=t)

	@classmethod
	def dev_paths(cls):
		"""Override to register your device type. Generates
		tuples of prefixes; the device class (instead of ':dev') must be
		the last element."""
		return ()

	# Note that while the interface to the following three generic handlers
	# is the same across all device types, the actual implementation
	# typically accesses environment variables without which it doesn't
	# work.

	async def read(self,what):
		"""Read from the device. This code does NOT update etcd."""
		raise NotImplementedError("I don't know how to read '%s' from %s" % (what,repr(self)))

	async def write(self,what, value):
		"""Write to the device. This code does NOT update etcd."""
		raise NotImplementedError("I don't know how to write '%s' to '%s' of %s" % (value,what,repr(self)))

	async def poll(self):
		"""Poll this device. The default does nothing."""
		pass

class TypedSubdir(ManagedEtcThing,EtcDir):
	pass

for attr in _SOURCES:
	BaseDevice.register(attr, cls=TypedSubdir)

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

class _ManagedDir(ManagedEtcThing,EtcDir):
	pass

class Device(ManagedEtcDir, BaseDevice):
	"""\
		This is the superclass for devices that actually work
		(or are supposed to work). Use this instead of BaseDevice
		unless you have a very good reason not to.

		Specifically, DeadDevice does not implement any AMQP hooks.
		"""
	prefix = None
	description = "Override me"

	@classmethod
	async def this_obj(cls, recursive, **kw):
		if not recursive:
			raise ReloadRecursive
		return (await super().this_obj(recursive=recursive, **kw))

	async def set_managed(self, mgr):
		"""Async manager callback after adding a manager"""
		await super().set_managed(mgr)
		await self.set_manager(mgr)

	async def set_unmanaged(self):
		"""Async manager callback after killing a manager"""
		await super().set_unmanaged()
		await self.set_manager(None)

	@classmethod
	def types(cls, types):
		"""\
			Register value types with etcd_tree.
			Override to add your own categories; add to your
			input{}/output{} for atomic values"""

		for d in _SOURCES:
			types.register(d,_ManagedDir)
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
				missing[k] = dd = {'type':v,'created':time()}
				v = type_names()[v]
				if v.default is not None:
					dd['value'] = v(value=v.default).etcd_value
			if missing:
				await self.set(d,missing)
				# Note that this does not delete anything not mentioned

	async def teardown(self):
		"""\
			Processing when this device gets deleted.
			"""
		pass
			

	async def manager_present(self, mgr):
		pass
	def manager_gone(self):
		pass

	async def reading(self,what,value, timestamp=None):
		"""We have an input value"""
		await self['input'][what].reading(value, timestamp)

	async def writing(self,what,value, timestamp=None):
		"""We have an output value"""
		await self['output'][what].writing(value,timestamp)

