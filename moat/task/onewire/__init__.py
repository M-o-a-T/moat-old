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
import pytest
from time import time

from moat.proto.onewire import OnewireServer
from moat.dev.onewire import OnewireDevice
from moat.script.task import Task
from moat.script.util import objects

from etcd_tree.node import mtFloat,mtInteger,mtValue,mtDir
from etcd_tree.etcd import EtcTypes
from aioetcd import StopWatching
from time import time
from weakref import WeakValueDictionary
from contextlib import suppress

import logging
logger = logging.getLogger(__name__)

import re
dev_re = re.compile(r'([0-9a-f]{2})\.([0-9a-f]{12})$', re.I)

# This is here for overriding by tests.
async def Timer(loop,dly,proc):
	return loop.call_later(dly, proc._timeout)

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
		self.bus = parent.srv
		super().__init__(parent.env.cmd,('onewire','scan',self.typ,self.env.srv_name)+self.bus.path)

	async def task(self):
		"""run task_() periodically."""
		ts = time()
		long_warned = 0
		while True:
			if self._trigger is None or self._trigger.done():
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

class mtBus(mtDir):
	tasks = None

	def __init__(self,*a,**k):
		super().__init__(*a,**k)
		self.tasks = WeakValueDictionary()
		self.timers = {}
		self.srv = self.env.srv.at('uncached').at(*(self.name.split(' ')))

	@property
	def devices(self):
		d = self.env.devices
		for f1,v in self['devices'].items():
			for f2,b in v.items():
				if b > 0:
					continue
				dev = d[f1][f2][':dev']
				yield dev

	def has_update(self):
		super().has_update()
		if self._seq is None:
			print("UPD DOWN",self,self.srv.path,list(self.tasks.keys()))
			t,self.tasks = self.tasks,{}
			for v in t.values():
				t.cancel()
		else:
			if not tasks:
				for t in objects(__name__,ScanTask):
					tasks[t.typ] = t
			for name,task in tasks.items():
				t = None
				for dev in self.devices:
					f = dev.scan_for(name)
					if f is None:
						pass
					elif t is None or t > f:
						t = f

				self.timers[name] = t
				if t is not None and name not in self.tasks:
					print("UPD UP",self,self.srv.path,name)
					self.tasks[name] = self.env.add_task(task(self))
		
class BusScan(Task):
	"""This task periodically scans all buses of a 1wire server."""
	name="onewire/scan"
	summary="Scan the buses of a 1wire server"
	_delay = None
	_delay_timer = None

	@classmethod
	def types(cls,tree):
		super().types(tree)
		tree.register("delay",cls=mtFloat)
		tree.register("update_delay",cls=mtFloat)
		tree.register("ttl",cls=mtInteger)
		
	async def _scan_one(self, *bus):
		"""Scan a single bus"""
		b = " ".join(bus)
		bb = self.srv_name+" "+b

		old_devices = set()
		try:
			k = self.old_buses.remove(b)
		except KeyError:
			# The bus is new
			logger.info("New 1wire bus: %s",bb)

			await self.tree['bus'].set(b,{'broken':0,'devices':{}})
			dev_counter = self.tree['bus'][b]['devices']
		else:
			# The bus is known. Remember which devices we think are on it
			dev_counter = self.tree['bus'][b]['devices']
			for d,v in dev_counter.items():
				for e in v.keys():
					old_devices.add((d,e))

		for f in await self.srv.dir('uncached',*bus):
			m = dev_re.match(f)
			if m is None:
				continue
			f1 = m.group(1).lower()
			f2 = m.group(2).lower()
			if (f1,f2) in old_devices:
				old_devices.remove((f1,f2))
			if f1 == '1f':
				await self._scan_one(*(bus+(f,'main')))
				await self._scan_one(*(bus+(f,'aux')))

			if f1 not in self.devices:
				await self.devices.set(f1,{})
			if f2 not in self.devices[f1]:
				await self.devices[f1].set(f2,{':dev':{'path':bb}})
			fd = self.devices[f1][f2][':dev']
			op = fd.get('path','')
			if op != bb:
				if ' ' in op:
					self.drop_device(fd,delete=False)
				await fd.set('path',bb)

			if f1 not in dev_counter:
				await dev_counter.set(f1,{})
			if f2 not in dev_counter[f1]:
				await dev_counter[f1].set(f2,0)

		# Now mark devices which we didn't see as down.
		# Protect against intermittent failures.
		for f1,f2 in old_devices:
			try:
				v = dev_counter[f1][f2]
			except KeyError: # pragma: no cover
				# possible race condition
				continue
			if v >= DEV_COUNT:
				# kill it.
				try:
					dev = self.devices[f1][f2][':dev']
				except KeyError:
					pass
				else:
					await self.drop_device(dev)
			else:
				# wait a bit
				await dev_counter[f1].set(f2,v+1)

		# Mark this bus as "scanning OK".
		try:
			v = self.tree['bus'][b]['broken']
		except KeyError:
			v = 99
		if v > 0:
			await self.tree['bus'][b].set('broken',0)

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
			if s == self.srv_name:
				dt = self.tree['bus'][b]['devices']
				drop = False
			else:
				dt = await self.etcd.tree('/bus/onewire/'+s+'/bus/'+b+'/devices',env=self)
				drop = True
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
			finally:
				if drop:
					await dt.close()
		if delete:
			await dev.delete('path')

	async def drop_bus(self,bus):
		logger.warning("Bus '%s %s' has vanished", self.srv_name,bus.name)
		for f1,v in bus.items():
			for f2 in bus.keys():
				try:
					dev = self.devices[f1][f2][':dev']
				except KeyError:
					pass
				else:
					await self.drop_device(dev, delete=False)
			await self.tree['bus'].delete(bus.name)

	def add_task(self, t):
		t = asyncio.ensure_future(t, loop=self.loop)
		self.new_tasks.add(t)
		if not self._trigger.done():
			self._trigger.set_result(None)
		return t

	async def task(self):
		self.srv = None
		self.tree = None
		self.srv_name = None
		types=EtcTypes()
		types.register('*','*',':dev', cls=OnewireDevice)

		update_delay = self.config.get('update_delay',None)
		self.devices = await self.etcd.tree("/device/onewire",env=self,types=types, update_delay=update_delay)
		self._trigger = None

		main_task = asyncio.ensure_future(self.task_busscan(), loop=self.loop)
		self.tasks = {main_task}
		self.new_tasks = set()
		try:
			while not main_task.done():
				if self._trigger is None or self._trigger.done():
					self._trigger = asyncio.Future(loop=self.loop)
					self.tasks.add(self._trigger)
				d,p = await asyncio.wait(self.tasks, loop=self.loop, return_when=asyncio.FIRST_COMPLETED)
				if self.new_tasks:
					p |= self.new_tasks
					self.new_tasks = set()
				for t in d:
					try:
						t.result()
					except asyncio.CancelledError as exc:
						logger.info("Cancelled: %s", t)
				self.tasks = p

		except BaseException as exc:
			logger.exception("interrupted?")
			p = self.tasks
			raise
		finally:
			print("F",p)
			for t in p:
				if not t.done():
					t.cancel()
			asyncio.wait(p, loop=self.loop, return_when=asyncio.ALL_COMPLETED)
		for t in d:
			t.result()
			# this will re-raise whatever exception triggered the first wait

	async def task_busscan(self):
		types=EtcTypes()
		types.register('port', cls=mtInteger)
		types.register('scanning', cls=mtFloat)
		types.register('bus','*', cls=mtBus)
		types.register('bus','*','broken', cls=mtInteger)
		types.register('bus','*','devices','*','*', cls=mtInteger)

		while True:
			if self.config['delay']:
				self._delay = asyncio.Future(loop=self.loop)
				self._delay_timer = await Timer(self.loop,self.config['delay'], self)

			# Access "our" server
			server = self.config['server']
			if self.srv_name is None or self.srv_name != server:
				if self.srv is not None:
					await self.srv.close()
				self.srv_name = server
				update_delay = self.config.get('update_delay',None)
				self.tree = await self.etcd.tree("/bus/onewire/"+server, types=types,env=self,update_delay=update_delay)
				self.srv = OnewireServer(self.tree['host'],self.tree.get('port',None), loop=self.loop)

			if 'scanning' in self.tree:
				# somebody else is processing this bus. Grumble.
				logger.info("Server '%s' locked.",self.srv_name)
				tree._get('scanning').add_monitor(self._unlock)
				continue
			await self.tree.set('scanning',value=time(),ttl=BUS_TTL)
			try:
				self.old_buses = set()
				if 'bus' in self.tree:
					for k in self.tree['bus'].keys():
						self.old_buses.add(k)
				else:
					await self.tree.set('bus',{})
				for bus in await self.srv.dir('uncached'):
					if bus.startswith('bus.'):
						await self._scan_one(bus)

				# Delete buses which haven't been seen for some time
				# (to protect against intermittent failures)
				for bus in self.old_buses:
					bus = self.tree['bus'][bus]
					v = bus['broken']
					if v < BUS_COUNT:
						logger.info("Bus '%s' not seen",bus)
						await bus.set('broken',v+1)
					else:
						await self.drop_bus(bus)

			finally:
				if not self.tree.stopped.done():
					await self.tree.delete('scanning')

			if self._delay is None:
				break
			try:
				await self._delay
				self._delay.result()
			except StopWatching:
				break
			if self.tree.stopped.done():
				return self.tree.stopped.result()
	
	def _timeout(self,exc=None):
		"""Called from timer"""
		if self._delay is not None and not self._delay.done():
			if exc is None:
				self._delay.set_result("timeout")
			else:
				# This is for the benefit of testing
				self._delay.set_exception(exc)

	def trigger(self):
		"""Tell all tasks to run now. Used mainly for testing."""
		if self._delay is not None and not self._delay.done():
			self._delay.set_result("cfg_changed")
			self._delay_timer.cancel()
		for t in self.tasks:
			if hasattr(t,'trigger'):
				t.trigger()

	def cfg_changed(self):
		"""Called from task machinery when my configuration changes"""
		if self._delay is not None and not self._delay.done():
			self._delay.set_result("cfg_changed")
			self._delay_timer.cancel()

	def _unlock(self,node): # pragma: no cover
		"""Called when the 'other' scanner exits"""
		if node._seq is not None:
			return
		if self._delay is not None and not self._delay.done():
			self._delay.set_result("unlocked")
			self._delay_timer.cancel()

