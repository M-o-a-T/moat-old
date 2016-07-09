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
from etcd_tree.node import EtcFloat,EtcInteger,EtcString, EtcDir,EtcXValue, EtcAwaiter
from time import time

from moat.bus.base import Bus
from moat.types.etcd import MoatBusBase, Subdirs, recEtcDir
from moat.types.managed import ManagedEtcDir,ManagedEtcThing
from moat.dev import DEV_DIR,DEV

from .task import tasks
from .dev import OnewireDevice


class OnewireBusBase(MoatBusBase):
	"""Directory for /bus/onewire"""
	@property
	def task_monitor(self):
		return Subdirs(self)
	def task_for_subdir(self,d):
		return True

class OnewireBus(ManagedEtcDir, recEtcDir, Bus):
	"""Directory for /bus/onewire/NAME"""
	prefix = "onewire"
	description = "A controller for 1wire"

	@property
	def task_monitor(self):
		yield "add",'onewire/run', ('onewire',self.name,'run'), {}
		yield "add",'onewire/scan', ('onewire',self.name,'scan'), {}
		yield "scan",('bus','onewire',self.name,'bus'), {}

class OnewireBusSub(ManagedEtcThing, EtcDir):
	"""Directory for /bus/onewire/NAME/bus"""
	@property
	def task_monitor(self):
		return Subdirs(self)
	def task_for_subdir(self,d):
		return True

class OnewireBusOne(ManagedEtcThing, EtcDir):
	"""Directory for /bus/onewire/NAME/bus/BUS"""
	@property
	def task_monitor(self):
		yield "add",'onewire/scan/bus', ('onewire',self.path[2],'scan',self.name), {}
		yield "scan",('bus','onewire',self.path[2],'bus',self.path[4],'devices'), {}
	def task_for_subdir(self,d):
		return True

class OnewireBusDevs(ManagedEtcThing, EtcDir):
	"""Directory for /bus/onewire/NAME/bus/BUS/devices"""
	@property
	def task_monitor(self):
		return Subdirs(self)
	def task_for_subdir(self,d):
		return True

class _OnewireBusDev_dev_iter(object):
	def __init__(self, d,name, items):
		self.d = d
		self.name = name
		self.items = items
	async def __aiter__(self):
		self.i = iter(self.items())
		return self
	async def __anext__(self):
		try:
			while True:
				f2,b = next(self.i)
				if b.value > 0:
					continue
				try:
					dev = self.d[self.name][f2][DEV]
					dev = (await dev)
					return dev
				except KeyError:
					continue
		except StopIteration:
			pass
		raise StopAsyncIteration


class _OnewireBusDev_task_iter(object):
	def __init__(self, path,devices,items):
		self.path = path
		self.devices = devices
		self.items = items
	async def __aiter__(self):
		self.i = iter(self.items())
		return self
	async def __anext__(self):
		try:
			while True:
				name,task = next(self.i)
				t = None
				async for dev in self.devices:
					f = dev.scan_for(name)
					if f is None:
						pass
					elif t is None or t > f:
						t = f

				if t is not None:
					return "add",'onewire/run/'+name,('onewire',self.path[2],'run',self.path[4],name),{'timer':t}
		except StopIteration:
			pass
		raise StopAsyncIteration


class OnewireBusDev(ManagedEtcThing, EtcDir):
	"""Directory for /bus/onewire/NAME/bus/BUS/devices/XX"""

	def task_for_subdir(self,d):
		return True

	@property
	def devices(self):
		d = self.root.lookup(*DEV_DIR, name='onewire')
		return _OnewireBusDev_dev_iter(d,self.name, self.items)

	@property
	def task_monitor(self):
		return _OnewireBusDev_task_iter(self.path,self.devices, tasks().items)

class OnewireBusDevice(ManagedEtcThing, EtcXValue):
	"""\
		Entry for /bus/onewire/NAME/bus/BUS/devices/XX/YYYYYYYYYYYY
		The .value attribute holds the number of consecutive failed
		attempts to find this device by scanning the bus it's supposed to
		be on.
		"""
	type = int
	@property
	def device(self):
		dev = self.root.lookup(*DEV_DIR).lookup('onewire',self.parent.name,self.name,DEV)
		return dev

	async def manager_present(self,mgr):
		dev = await self.device
		# TODO: make sure its path is correct
		try:
			mgr.add_device(dev)
		except AttributeError:
			import pdb;pdb.set_trace()
			pass
	def manager_gone(self):
		if isinstance(self.device,EtcAwaiter):
			return
		try:
			self.device.manager_gone()
		except AttributeError:
			import pdb;pdb.set_trace()
			pass
		

OnewireBusBase.register('*',cls=OnewireBus)
OnewireBus.register("server","host", cls=EtcString)
OnewireBus.register("server","port", cls=EtcInteger)
OnewireBus.register('bus', cls=OnewireBusSub)
OnewireBusSub.register('*', cls=OnewireBusOne)
OnewireBusOne.register('broken', cls=EtcInteger)
OnewireBusOne.register('devices', cls=OnewireBusDevs)
OnewireBusDevs.register('*', cls=OnewireBusDev)
OnewireBusDev.register('*', cls=OnewireBusDevice)

