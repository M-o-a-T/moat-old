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

import logging
logger = logging.getLogger(__name__)
from etcd_tree.node import EtcFloat,EtcInteger,EtcString
from time import time

from moat.dev import DEV
from moat.dev.base import Device, _SOURCES
from moat.types.etcd import MoatDeviceBase

class NoAlarmHandler(RuntimeError):
	pass

_device_types = {} # cache
def device_types():
	if not _device_types:
		from moat.script.util import objects
		for typ in objects(__name__,OnewireDevice):
			fam = typ.family
			if isinstance(fam,str):
				_device_types[fam] = typ
			else:
				for f in fam:
					_device_types[f] = typ
	return _device_types

class OnewireDeviceBase(MoatDeviceBase):
	"""Base class for /device/onewire"""
	def subtype(self,*path,**kw):
		if len(path) != 3 or path[-1] != DEV:
			return super().subtype(self,*path,**kw)
		try:
			return device_types()[path[0]]
		except KeyError:
			class OWdevice(OnewireDevice):
				name = '?'+path[0]
			return OWdevice

class OnewireDevice(Device): #(, metaclass=SelectDevice):
	"""Base class for /device/onewire/XX/YYYYYYYYYYYY/:dev"""
	prefix = "onewire"
	name = "generic"
	description = "Something hanging off 1wire"
	_inited = False
	_cached_path = None

	async def init(self):
		await super().init()
		if type(self) == OnewireDevice:
			self.name = type(self).name+' '+self.parent.parent.name

	@property
	async def bus_dev(self):
		n = self['path'].split(' ')[1:]
		logger.debug("msync A")
		m = await self.manager_async
		logger.debug("msync B")
		return m.bus.at(*n).at(self.path[-3]+'.'+self.path[-2])

#	def has_update(self):
#		super().has_update()
#		env = self.env.onewire_run
#		if env is None:
#			return
#
#		srvpath = self.get('path','')
#		if self._cached_path is None or srvpath != self._cached_path:
#			if srvpath != '':
#				srv,path = srvpath.split(' ',1)
#				assert env.srv_name == srv
#				self.bus = env.srv.at('uncached').at(*path.split(' ')).at(self.parent.parent.name+'.'+self.parent.name)
#				self.bus_cached = env.srv.at(*path.split(' ')).at(self.parent.parent.name+'.'+self.parent.name)
#			else:
#				self.bus = None
#				self.bus_cached = None
#			self._cached_path = srvpath

	def scan_for(self, what):
		"""\
			Task selection.

			'what' is a task name, from moat/ext/onewire/task/*.
			If this returns a number N, the task will execute
			at least every N seconds, on the bus the device is on.

			Examples:
			'alarm' polls for devices which respond to Conditional Search
			'temperature' triggers a conversion, waits, and then reads all devices' temperature.
			"""
		return None
	
	async def has_alarm(self):
		raise NoAlarmHandler(self)

