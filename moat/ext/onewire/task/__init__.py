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

import asyncio
from time import time
from weakref import WeakValueDictionary

from etcd_tree import EtcTypes, EtcFloat,EtcInteger,EtcValue,EtcDir
from aio_etcd import StopWatching

from contextlib import suppress
from moat.dev import DEV_DIR,DEV
from moat.bus import BUS_DIR
from moat.script.task import Task,TimeoutHandler
from moat.script.util import objects
from moat.task.device import DeviceMgr

from ..proto import OnewireServer
from ..dev import OnewireDevice

import logging
logger = logging.getLogger(__name__)

import re
dev_re = re.compile(r'([0-9a-f]{2})\.([0-9a-f]{12})$', re.I)

BUS_TTL=30 # presumed max time required to scan a bus
BUS_COUNT=5 # times to not find a whole bus before it's declared dead
DEV_COUNT=5 # times to not find a single device on a bus before it is declared dead

async def scanner(self, name):
	proc = getattr(self,'_scan_'+name)
	while True:
		warned = await proc()

class _BusTask(Task):
	schema = {'update_delay':'float/time'}

	@property
	def update_delay(self):
		try:
			return self['update_delay']
		except KeyError:
			return self.parent.update_delay

	async def setup(self):
		# onewire/NAME/scan/…
		await super().setup()
		self.srv_name = self.path[1]
		self.srv_tree = await self.tree.lookup(BUS_DIR+('onewire',self.srv_name))

		self.srv_data = await self.srv_tree['server']
		self.srv = OnewireServer(self.srv_data['host'],self.srv_data.get('port',None), loop=self.loop)
		self.devices = await self.tree.subdir(DEV_DIR+('onewire',))

	async def teardown(self):
		try:
			await self.srv.close()
		except Exception:
			logger.exception("closing down")
		await super().teardown()

class _ScanMeta(type(_BusTask)):
	"""Metaclass to set up ScanTask subclasses correctly"""
	def __init__(cls, name, bases, nmspc):
		super(_ScanMeta, cls).__init__(name, bases, nmspc)
		typ = nmspc.get('typ',None)
		if typ is not None:
			cls.taskdef='onewire/run/'+typ
	
class BusHandler(_BusTask,DeviceMgr):
	"""\
		Manager task, handles interfacing with AMQP
		"""
	taskdef = "onewire/run"
	summary = "Interface between a 1wire master, its devices, and AMQP"
	async def setup(self):
		"""\
			additional setup before DeviceMgr.task()
			"""
		await super().setup()
		self.bus = self.srv.at('uncached')
		self.bus_cached = self.srv
	
	async def managed(self):
		managed = await self.tree['bus']
		managed = await managed.lookup(*self.path[:-1])
		return managed

class ScanTask(TimeoutHandler, _BusTask, metaclass=_ScanMeta):
	"""\
		Common class for 1wire bus scanners.

		Subclasses override the `typ` class variable with some name, and
		the `task_()` method with the periodic activity they want to
		perform. Whenever a device's `scan_for(typ)` procedure returns a
		number, a ScanTask instance with that type will be created for the
		bus the device is on, which will run the task at least that often
		(in seconds).

		
		"""
	typ = None
	schema = {'timer':'float'}

	async def task(self):
		"""\
			run task_() periodically.
			
			Do not override this; override .task_ instead.
			"""
		logger.debug("starting %s: %s",self.__class__.__name__,self.path)
		self.parent = await self.tree['bus']['onewire'][self.taskdir.path[2]]['bus'][self.taskdir.path[4]]
		await self.parent['devices'] # we need that later

		path = self.path[3].split(' ')
		self.bus = self.srv.at('uncached').at(*path)
		self.bus_cached = self.srv.at(*path)

		ts = time()
		try:
			t = self.config['timer']
		except KeyError:
			t = self.taskdir['data']['timer']
		long_warned = 0

		while True:
			logger.debug("taskBeg %d %s", id(self),self)
			try:
				warned = await self.task_()
			except Exception as exc:
				logger.exception("tasking %d %s", id(self),self)
				raise
			else:
				logger.debug("tasking %d %s", id(self),self)

			# subtract the time spent during the task
			if warned and t < 10:
				t = 10
			ts += t
			nts = time()
			delay = ts - nts
			if delay < 0:
				if not long_warned:
					long_warned = int(100/t)+1
					# thus we get at most one warning every two minutes, more or less
					logger.warning("Task %s took %s seconds, should run every %s",self.name,t-delay,t)
					# TODO: write that warning to etcd
				ts = nts

				# don't loop endlessly
				#continue
				delay = 0.01
			elif long_warned:
				long_warned -= 1
			logger.debug("taskEnd %d %s", id(self),self)
			await self.delay(delay)

	async def task_(self):
		"""Override this to actually implement the periodic activity."""
		raise RuntimeError("You need to override '%s.task_'" % (self.__class__.__name__,))

class _BusScan(_BusTask):
	"""Common code for bus scanning"""

	async def setup(self):
		await super().setup()
		self.buses = await self.srv_tree.subdir('bus')

	async def drop_device(self,dev, delete=True):
		"""When a device vanishes, remove it from the bus it has been at"""
		try:
			p = dev['path']
		except KeyError:
			return
		try:
			s,b = p.split(' ',1)
		except ValueError:
			pass
		else:
			dt = await self.tree.lookup('bus','onewire',s,'bus',b,'devices')
			try:
				f1 = dev.parent.parent.name
				f2 = dev.parent.name
			except AttributeError:
				pass # parent==None: node gone, don't bother
			else:
				try:
					await dt[f1].delete(f2)
				except KeyError as exc:
					logger.exception("Bus node gone? %s.%s on %s %s",f1,f2,s,b)
		if delete:
			await dev.delete('path')

	async def drop_bus(self,bus):
		"""Somebody unplugged a whole bus"""
		logger.warning("Bus '%s %s' has vanished", self.srv_name,bus.name)
		for f1,v in bus.items():
			for f2 in bus.keys():
				try:
					dev = await self.devices[f1][f2][DEV]
				except KeyError:
					pass
				else:
					await self.drop_device(dev, delete=False)
			await self.tree['bus'].delete(bus.name)

class BusScan(_BusScan):
	"""This task scans a specific bus of a 1wire server: /task/onewire/DEV/scan/BUS."""
	taskdef="onewire/scan/bus"
	summary="Scan one bus of a 1wire server"

	async def task(self):
		"""Scan a single bus"""
		bus_name = self.path[3]
		bus = bus_name.split(' ')

		bb = self.srv_name+" "+bus_name

		old_devices = set()
		bus_dir = await self.buses[bus_name]
		dev_counter = await bus_dir.subdir('devices')
		for d,v in dev_counter.items():
			for e in (await v).keys():
				old_devices.add((d,e))

		for f in await self.srv.dir('uncached',*bus):
			m = dev_re.match(f)
			if m is None:
				continue
			f1 = m.group(1).lower()
			f2 = m.group(2).lower()
			if (f1,f2) in old_devices:
				old_devices.remove((f1,f2))

			if f1 not in self.devices:
				await self.devices.set(f1,{})
			d = await self.devices[f1]
			if f2 not in d:
				await self.devices[f1].set(f2,{DEV:{'path':bb}})
			fd = await d[f2][DEV]
			op = fd.get('path','')
			if op != bb:
				if ' ' in op:
					await self.drop_device(fd,delete=False)
				await fd.set('path',bb)

			if f1 not in dev_counter:
				await dev_counter.set(f1,{})
			if f2 not in dev_counter[f1]:
				await dev_counter[f1].set(f2,0)

			await fd.setup()

		# Now mark devices which we didn't see as down.
		# Protect against intermittent failures.
		for f1,f2 in old_devices:
			try:
				errors = dev_counter[f1][f2].value
			except KeyError: # pragma: no cover
				# possible race condition
				continue
			if errors >= DEV_COUNT:
				# kill it.
				try:
					dev = self.devices[f1][f2][DEV]
				except KeyError:
					pass
				else:
					await self.drop_device(dev)
			else:
				# wait a bit
				await dev_counter[f1].set(f2,errors+1)

		# Mark this bus as "scanning OK".
		try:
			errors = bus_dir['broken']
		except KeyError:
			errors = 99
		if errors > 0:
			await bus_dir.set('broken',0)

class BusScanBase(_BusScan):
	"""This task enumerates all (root) buses of a 1wire server: /task/onewire/DEV/scan"""
	taskdef="onewire/scan"
	summary="Scan the 'root' buses of a 1wire server"

	async def task(self):
		old_buses = set()
		for k in self.buses.keys():
			if k.startswith('bus.') and ' ' not in k:
				old_buses.add(k)

		for bus in await self.srv.dir('uncached'):
			if bus.startswith('bus.'):
				try:
					k = old_buses.remove(bus)
				except KeyError:
					# The bus is new
					logger.info("New 1wire bus: %s %s",self.srv_name,bus)
					await self.buses.set(bus,{'broken':0,'devices':{}})

		# Delete buses which haven't been seen for some time
		# (to protect against intermittent failures)
		for bus in old_buses:
			bus = self.buses[bus]
			v = bus['broken']
			if v < BUS_COUNT:
				logger.info("Bus '%s' not seen",bus)
				await bus.set('broken',v+1)
			else:
				await self.drop_bus(bus)

_tasks = {}

def tasks():
	if not _tasks:
		for t in objects(__name__,ScanTask):
			_tasks[t.typ] = t
	return _tasks

