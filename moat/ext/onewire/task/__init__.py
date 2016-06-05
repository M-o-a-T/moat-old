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

import asyncio
from time import time
from weakref import WeakValueDictionary

from etcd_tree import EtcTypes, EtcFloat,EtcInteger,EtcValue,EtcDir
from aio_etcd import StopWatching

from contextlib import suppress
from moat.dev import DEV_DIR,DEV
from moat.bus import BUS_DIR
from moat.script.task import Task
from moat.script.util import objects

from ..proto import OnewireServer
from ..dev import OnewireDevice

import logging
logger = logging.getLogger(__name__)

import re
dev_re = re.compile(r'([0-9a-f]{2})\.([0-9a-f]{12})$', re.I)

async def trigger_hook(loop):
	"""\
		This code is intended to be overridden by tests.

		It returns a future which, when completed, should cause any
		activity to run immediately which otherwise waits for a timer.
		
		The default implementation does nothing but return a static future
		that's never completed.

		Multiple calls to this code must return the same future as long as
		that future is not completed.
		"""
	try:
		return loop._moat_open_future
	except AttributeError:
		loop._moat_open_future = f = asyncio.Future(loop=loop)
		return f

BUS_TTL=30 # presumed max time required to scan a bus
BUS_COUNT=5 # times to not find a whole bus before it's declared dead
DEV_COUNT=5 # times to not find a single device on a bus before it is declared dead

async def scanner(self, name):
	proc = getattr(self,'_scan_'+name)
	while True:
		warned = await proc()

tasks = {} # filled later

class ScanTask(Task):
	"""\
		Common class for 1wire bus scanners.

		Subclasses override the `typ` class variable with some name, and
		the `task_()` method with the periodic activity they want to
		perform. Whenever a device's `scan_for(typ)` returns a number, a
		ScanTask instance with that type will be created for the bus the
		device is on, which will run the task at least that often (in
		seconds).

		
		"""
	typ = None
	_trigger = None

	def __init__(self,parent):
		self.parent = parent
		self.env = parent.env
		self.bus = parent.bus
		self.bus_cached = parent.bus_cached
		super().__init__(parent.env.cmd,('onewire','scan',self.typ,self.env.srv_name)+self.bus.path)

	async def task(self):
		"""\
			run task_() periodically.
			
			Do not override this; override .task_ instead.
			"""
		ts = time()
		long_warned = 0
		while True:
			if self._trigger is None or self._trigger.done():
				if self._trigger is not None:
					try:
						self._trigger.result()
					except StopWatching:
						break
					# propagate an exception, if warranted
				self._trigger = asyncio.Future(loop=self.loop)
			warned = await self.task_()
			t = self.parent.timers[self.typ]
			if t is None:
				return
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
					# TODO: write that warning to etcd instead
				ts = nts
				continue
			elif long_warned:
				long_warned -= 1
			with suppress(asyncio.TimeoutError):
				await asyncio.wait_for(self._trigger,delay, loop=self.loop)

	def trigger(self):
		"""Call to cause an immediate re-scan"""
		if self._trigger is not None and not self._trigger.done():
			self._trigger.set_result(None)

	async def task_(self):
		"""Override this to actually implement the periodic activity."""
		raise RuntimeError("You need to override '%s.task_'" % (self.__class__.__name__,))

class _BusTask(Task):
	schema = {'delay':'float/time','update_delay':'float/time','ttl':'int'}
	@classmethod
	def types(cls,tree):
		super().types(tree)
		tree.register("delay",cls=EtcFloat)
		tree.register("update_delay",cls=EtcFloat)
		tree.register("ttl",cls=EtcInteger)

	async def setup_vars(self):
		# onewire/NAME/scan/…
		self.srv_name = self.path[1]
		self.srv_tree = await self.tree.lookup(BUS_DIR+('onewire',self.srv_name))
		self.buses = await self.srv_tree.subdir('bus')

		self.srv_data = await self.srv_tree['server']
		self.srv = OnewireServer(self.srv_data['host'],self.srv_data.get('port',None), loop=self.loop)
		self.devices = await self.tree.subdir(DEV_DIR+('onewire',))

class _BusScan(_BusTask):
	"""Common code for bus scanning"""
	_delay = None
	_delay_timer = None

	async def drop_device(self,dev, delete=True):
		"""When a device vanishes, remove it from the bus it has been at"""
		await self.deleted()
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
	_delay = None
	_delay_timer = None

	async def task(self):
		"""Scan a single bus"""
		await self.setup_vars()
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

			await fd.created()

		# Now mark devices which we didn't see as down.
		# Protect against intermittent failures.
		for f1,f2 in old_devices:
			try:
				errors = dev_counter[f1][f2]
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
		await self.setup_vars()

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

#class EtcOnewireBus(EtcDir):
#	tasks = None
#	_set_up = False
#
#	def __init__(self,*a,**k):
#		super().__init__(*a,**k)
#		self.tasks = WeakValueDictionary()
#		self.timers = {}
#		env = self.env.onewire_common
#		if srv:
#			self.bus = env.srv.at('uncached').at(*(self.name.split(' ')))
#			self.bus_cached = env.srv.at(*(self.name.split(' ')))
#
#	@property
#	def devices(self):
#		d = self.env.onewire_common
#		if d is None:
#			return
#		d = d.devices
#		for f1,v in self['devices'].items():
#			for f2,b in v.items():
#				if b > 0:
#					continue
#				try:
#					dev = d[f1][f2][DEV]
#				except KeyError:
#					continue
#				if not isinstance(dev,OnewireDevice):
#					# This should not happen. Otherwise we'd need to
#					# convert .setup_tasks() into a task.
#					raise RuntimeError("XXX: bus lookup incomplete")
#				yield dev
#
#	def has_update(self):
#		super().has_update()
#		if self._seq is None:
#			logger.debug("Stopping tasks %s %s %s",self,self.bus.path,list(self.tasks.keys()))
#			if self.tasks:
#				t,self.tasks = self.tasks,WeakValueDictionary()
#				for v in t.values():
#					logger.info('CANCEL 16 %s',t)
#					t.cancel()
#		else:
#			self.setup_tasks()
#
#	def setup_tasks(self):
#		if not self.env.onewire_run:
#			return
#		if not tasks:
#			for t in objects(__name__,ScanTask):
#				tasks[t.typ] = t
#		for name,task in tasks.items():
#			t = None
#			for dev in self.devices:
#				f = dev.scan_for(name)
#				if f is None:
#					pass
#				elif t is None or t > f:
#					t = f
#
#			self.timers[name] = t
#			if t is not None:
#				if name not in self.tasks:
#					logger.debug("Starting task %s %s %s",self,self.bus.path,name)
#					self.tasks[name] = self.env.onewire_run.add_task(task(self))
#			else:
#				if name in self.tasks:
#					t = self.tasks.pop(name)
#					try:
#						t.cancel()
#					except Exception as ex:
#						logger.exception("Ending task %s for bus %s", name,self.bus.path)
#
#		self._set_up = True
#		
#EtcOnewireBus.register('broken', cls=EtcInteger)
#EtcOnewireBus.register('devices','*','*', cls=EtcInteger)
#
