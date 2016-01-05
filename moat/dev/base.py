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

from etcd_tree import EtcDir,EtcFloat, ReloadRecursive
from time import time

import logging
logger = logging.getLogger(__name__)

__all__ = ('Device',)

_SOURCES = ('input','output')

class Var(EtcDir):
	_type = None

	def __init__(self,*a,**k):
		super().__init__(*a,**k)

	def has_update(self):
		if 'type' not in self:
			self._type = None
			return
		if self._type is None or self._type.name != self['type']:
			self._type = self.env.types.subdir(self['type'],name=TYPE)

class BaseDevice(EtcDir):
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
			types.register(s,'*', cls=Var)

	@classmethod
	def dev_paths(cls):
		"""Override to register your device type. Generates
		tuples of prefixes; the device class (instead of ':dev') must be
		the last element."""
		return ()

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
		"""
	prefix = None
	description = "Override me"

	@classmethod
	async def this_class(cls, pre,recursive):
		if not recursive:
			raise ReloadRecursive
		return (await super().this_class(pre=pre,recursive=recursive))

	def has_update(self):
		"""\
			On first call: create variable entries if they don't exist yet.

			This is not asynchronous. If you need to talk to the device, TODO.
			"""
		super().has_update()
		if not self.notify_seq:
			# first time only
			d = {}
			for s in _SOURCES:
				d[s] = dd = {}
				src = self._get(s,{})
				for k,v in getattr(self,s,{}).items():
					if k not in src:
						dd[v] = {'type':v}
			self.update(d)

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
		if timestamp is None:
			timestamp = time()
		elif self['input'][what].get('timestamp',0) > timestamp:
			# a value from the past gets ignored
			return
		await self['input'][what].set('value',value)
		await self['input'][what].set('timestamp',timestamp)

	async def writing(self,what,value, timestamp=None):
		"""We have an output value"""
		if timestamp is None:
			timestamp = time()
		elif self['output'][what].get('timestamp',0) > timestamp:
			# setting a value to the past gets ignored
			return
		await self['output'][what].set('value',value)
		await self['output'][what].set('timestamp',timestamp)

