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
from dabroker.proto import ProtocolClient
from moat.proto.onewire import OnewireServer

from ..script.task import Task
from etctree.node import mtFloat,mtInteger
from etctree.etcd import EtcTypes
from aioetcd import StopWatching

import logging
logger = logging.getLogger(__name__)

import re
dev_re = re.compile(r'([0-9a-f]{2})\.([0-9a-f]{12})$', re.I)

# This is here for overriding by tests.
async def Timer(loop,dly,proc):
	return loop.call_later(self.cfg['delay'], self._trigger)

BUS_TTL=15 # presumed max time required to scan a bus
BUS_COUNT=5 # times to scan a bus before it's declared dead
DEV_COUNT=5 # times to scan a bus before a device on it is declared dead

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
		tree.register("ttl",cls=mtInteger)
		
	async def _scan_one(self, *bus):
		"""Scan a single bus"""
		b = " ".join(bus)
		bb = self.srv_name+" "+b
		old = set()
		try:
			k = self.buses.remove(b)
		except KeyError:
			# The bus is new
			m = await self.tree['bus'].set(b,{'broken':0,'devices':{}})
			await self.tree.wait(m)
			st = self.tree['bus'][b]['devices']
		else:
			# The bus is known. Remember which devices we think are on it
			st = self.tree['bus'][b]['devices']
			for d,v in st.items():
				for e in v.keys():
					old.add((d,e))

		for f in await self.srv.dir('uncached',*bus):
			m = dev_re.match(f)
			if m is None:
				continue
			f1 = m.group(1).lower()
			f2 = m.group(2).lower()
			if (f1,f2) in old:
				old.remove((f1,f2))
			if f1 == '1f':
				await self._scan_one(*(bus+(f,'main')))
				await self._scan_one(*(bus+(f,'aux')))

			if f1 not in self.devices:
				mod = await self.devices.set(f1,{})
				await self.devices.wait(mod)
			if f2 not in self.devices[f1]:
				m = await self.devices[f1].set(f2,{'path':bb})
				await self.devices.wait(m)
			fd = self.devices[f1][f2]
			op = fd.get('path','')
			if op != bb:
				if ' ' in op:
					self.drop_device(fd,delete=False)
				await fd.set('path',bb)

			if f1 not in st:
				mod = await st.set(f1,{})
				await self.tree.wait(mod)
			if f2 not in st[f1]:
				m = await st[f1].set(f2,0)
				await self.tree.wait(m)

		for f1,f2 in old:
			v = st[f1][f2]
			if v > DEV_COUNT:
				try:
					dev = self.devices[f1][f2]
				except KeyError:
					pass
				else:
					self.drop_device(dev)
			else:
				await st.set(f,v+1)

		try:
			v = self.tree['bus'][b]['broken']
		except KeyError:
			v = 99
		if v > 0:
			await self.tree['bus'][b].set('broken',0)

	async def drop_device(self,dev, delete=True):
		"""When a device vanishes, remove it from the bus it had been at"""
		p = dev['path']
		try:
			s,b = p.split(' ',1)
		except ValueError:
			pass
		else:
			if s == self.srv_name:
				dt = self.tree['bus'][b]
				drop = False
			else:
				dt = await self.etcd.tree('/bus/onewire/server/'+s+'/bus/'+b)
				drop = True
			try:
				await dt[dev.parent.name].delete(dev.name)
			except KeyError:
				pass
			finally:
				if drop:
					await dt.close()
		if delete:
			await self.devices[dev.parent.name].delete(dev.name)

	async def drop_bus(self,bus):
		for f1,v in bus.items():
			for f2 in bus.keys():
				try:
					dev = self.devices[f1][f2]
				except KeyError:
					pass
				else:
					await self.drop_device(dev, delete=False)
			await self.tree['bus'].delete(bus.name)
		pass

	async def task(self):
		self.srv = None
		self.tree = None
		self.srv_name = None
		types=EtcTypes()
		types.register('port', cls=mtInteger)
		types.register('scanning', cls=mtFloat)
		types.register('bus','*','broken', cls=mtInteger)
		types.register('bus','*','devices','*', cls=mtInteger)
		self.devices = await self.etcd.tree("/bus/onewire/device")

		while True:
			if self.config['delay']:
				self._delay = asyncio.Future(loop=self.loop)
				self._delay_timer = await Timer(self.loop,self.config['delay'], self._trigger)

			# Access "our" server
			server = self.config['server']
			if self.srv_name is None or self.srv_name != server:
				if self.srv is not None:
					await self.srv.close()
				self.srv_name = server
				self.tree = await self.etcd.tree("/bus/onewire/server/"+server, types=types)
				self.srv = OnewireServer(self.tree['host'],self.tree.get('port',None), loop=self.loop)

			if 'scanning' in self.tree:
				# somebody else is processing this bus. Grumble.
				logger.info("Server '%s' locked.",self.srv_name)
				tree._get('scanning').add_monitor(self._unlock)
				continue
			m = await self.tree.set('scanning',value=time(),ttl=BUS_TTL)
			await self.tree.wait(m)
			try:
				self.buses = set()
				if 'bus' in self.tree:
					for k in self.tree['bus'].keys():
						self.buses.add(k)
				else:
					mod = await self.tree.set('bus',{})
					await self.tree.wait(mod)
				for bus in await self.srv.dir('uncached'):
					if bus.startswith('bus.'):
						await self._scan_one(bus)
				for bus in self.buses:
					v = self.tree['bus'][bus]['broken']
					if v < BUS_COUNT:
						await self.tree['bus'][bus].set('broken',v+1)
					else:
						await self.drop_bus(bus)

			finally:
				await self.tree.delete('scanning')

			if self._delay is None:
				break
			try:
				await self._delay
			except StopWatching:
				break
	
	def _trigger(self,exc=None):
		if self._delay is not None and not self._delay.done():
			if exc is None:
				self._delay.set_result("timeout")
			else:
				# This is for the benefit of testing
				self._delay.set_exception(exc)

	def cfg_changed(self):
		if self._delay is not None and not self._delay.done():
			self._delay.set_result("cfg_changed")
			self._delay_timer.cancel()

	def _unlock(self,_):
		if self._delay is not None and not self._delay.done():
			self._delay.set_result("unlocked")
			self._delay_timer.cancel()

