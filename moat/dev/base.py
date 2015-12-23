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

import logging
logger = logging.getLogger(__name__)

from etcd_tree.node import mtDir,mtFloat

__all__ = ('Device','HardwareDevice')

_SOURCES = ('input','output')

class Device(mtDir):
	prefix = "dummy"
	description = "Something that does nothing."

	def __init__(self, *a,**k):
		for attr in _SOURCES:
			if not hasattr(self,attr):
				setattr(self,attr,{})
		super().__init__(*a,**k)

	@classmethod
	def types(cls, types):
		"""Override to get your subtypes registered with etcd_tree"""
		pass

	@staticmethod
	def dev_paths(cls, types):
		"""Override to register your device type. Returns a list/iter of
		tuples of prefixes; the device class (instead of ':dev') must be
		the last element."""
		yield '**',cls

class DeadDevice(Device):
	"""\
		This device has a wrong prefix, the code for it has been removed,
		or it's just plain wrong.
		"""
	name = 'dead'
	description = "Code not found"

class HardwareDevice(Device):
	prefix = None
	description = "Override me"

	def has_update(self):
		super().has_update()
		if not self.notify_seq:
			# first time only
			d = {}
			for k in _SOURCES:
				d[k] = dd = {}
				for k,v in getattr(self.k).items():
					dd[v] = {'type':v}
			self.update(d)

	@classmethod
	def types(cls, types):
		"""\
			Register value types with etcd_tree.
			Override to add your own categories; add to your
			input{}/output{} for atomic values"""

		for d in _SOURCES:
			types.register(d,'*','timestamp', cls=mtFloat)
			for k,v in getattr(cls,d,{}).items():
				v = value_types.get(v,mtValue)
				types.register(d,k,'value', cls=v)

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

