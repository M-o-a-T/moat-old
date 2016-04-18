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
from dabroker.unit import Unit,CC_DATA
from moat.ext.onewire.proto import OnewireServer
import mock
import aio_etcd as etcd
from contextlib import suppress

from . import ProcessHelper, is_open, MoatTest

import logging
logger = logging.getLogger(__name__)

class FakeSubBus:
	path = ()
	def __init__(self, parent,path):
		self.parent = parent
		self.path = path

	def __repr__(self):
		return "<S%s %s>" % (repr(self.parent), '/'.join(self.path),)

	async def dir(self,*p):
		return (await self.parent.dir(*(self.path+p)))

	async def read(self,*p):
		return (await self.parent.read(*(self.path+p)))

	async def write(self,*p, data=None):
		return (await self.parent.write(*(self.path+p), data=data))

	def at(self,*p):
		return FakeSubBus(parent=self,path=p)
		
class Fake_2405:
	val = False
	def __getitem__(self,k):
		if k != 'sensed':
			raise KeyError(k)
		return self.val

	def __setitem__(self,k,v):
		if k != 'pio':
			raise KeyError(k)
		import pdb;pdb.set_trace()
		if v == '1':
			self.val = False
		elif v == '0':
			self.val = True
		else:
			raise ValueError(v)

class FakeBus(FakeSubBus):
	def __init__(self, loop, data=None):
		self.loop = loop
		if data is not None:
			self.data = data
			return
		d=dict
		self.temp = {"temperature":12.5}
		self.moat = {}
		self.bus_main = {
			"alarm":{},
			"simultaneous":{},
			"f0.004200420042": self.moat,
			}
		self.bus_aux = {
			"alarm":{},
			"simultaneous":{},
			"10.001001001001":self.temp,
			}
		self.bus = {
			"alarm":{},
			"simultaneous":{},
			"1f.123123123123":{
				"main":self.bus_main,
				"aux":self.bus_aux,
				},
			"05.010101010101":Fake_2405(),
			}
		self.data = {
			"uncached": {
				"bus.42": self.bus,
				},
			"foobar":"whatever",
			"bus.42": self.bus,
			}

	def __repr__(self):
		return "<FakeBus>"

	def __call__(self, h,p, loop=None):
		assert h == "foobar.invalid"
		assert p == 4304
		assert self.loop is loop
		return self

	async def dir(self,*p):
		d = self.data
		for s in p:
			d = d[s.lower()]
		logger.debug("BUS.DIR %s %s",p,list(d.keys()))
		return d.keys()

	async def read(self,*p):
		d = self.data
		for s in p:
			d = d[s.lower()]
		assert not isinstance(d,dict)
		logger.debug("BUS.READ %s %s",p,d)
		return d

	async def write(self,*p, data=None):
		logger.debug("BUS.WRITE %s %s",p,data)
		d = self.data
		for s in p[:-1]:
			d = d[s.lower()]
		d[p[-1].lower()] = data

class Trigger:
	"""\
		A way to control task execution (and inject code) from a test.

		This does:
		* the main task async-__call__s this object, gets a future back
		* the test enters step(), which waits for the above __call__
		  if it hasn't yet, and triggers the future
		* if step() gets passed a procedure, that will be called by the
		  main task within __call__

		Usage:
		async def trigger_hook(obj,loop):
			return static_future_that_never_triggers
		class proc:
			async def loop(self):
				while True:
					f = await trigger_hook(self, self._loop)
					done,pending = await asyncio.wait((self.f,)+whatever_else_you_wait_for)
					…
			def trigger(self):
				self.f.set_result("trigger")
		…
		with mock.patch("moat.whatever.trigger_hook", new=Trigger(loop)) as fs:
			…
			await fs.step(f)
		
		"""

	f = None
	g = None
	obj = None
	mod = None
	trigger = None

	def __init__(self,loop=None):
		self.loop = loop
		self.trigger = asyncio.Future(loop=self.loop)

	async def __call__(self,loop=None):
		# called by the task when it wishes to create a timeout
		logger.debug("main: Enter")
		assert loop is None or self.loop is loop
		if self.trigger.done():
			self.trigger = asyncio.Future(loop=self.loop)

		if self.mod is not None:
			m,self.mod = self.mod,None
			logger.debug("main: Wait %s",m)
			await m()
		if self.f is not None:
			logger.debug("main: Sig")
			if not self.f.done():
				self.f.set_result(False)
		logger.debug("main: Exit")
		return self.trigger

	async def step(self, task, mod=False):
		"""\
			Trigger the fake timeout. @task is the task the timeout is
			running in so that we don't deadlock if it dies prematurely.
			@mod is a flag to signal StopWatching (if True), or a callback
			that's executed at the beginning of the next iteration.
			"""
		if not isinstance(mod,bool):
			# Register a state modifying function which the task shall
			# execute the next time it enters its main loop
			self.mod = mod
		
		self.f = asyncio.Future(loop=self.loop)
		if not self.trigger.done():
			logger.debug("step: trigger %s %s",self.trigger,id(self.trigger))
			self.trigger.set_result(None)
		logger.debug("step: Wait")
		await asyncio.wait((task,self.f), loop=self.loop,return_when=asyncio.FIRST_COMPLETED)
		self.f = None

		if mod is True:
			logger.debug("step: Kill %s",mod)
			self.trigger.set_exception(etcd.StopWatching())
			await task
		else:
			logger.debug("step: Run %s",mod)
			if task.done():
				task.result()
				assert False,"dead"

@pytest.yield_fixture
def owserver(loop,unused_tcp_port):
	port = unused_tcp_port
	p = ProcessHelper("owserver", "--foreground", "-p", port, "--tester=10", "--error_level", 5, "--error_print", 2, loop=loop)
	loop.run_until_complete(p.start())
	loop.run_until_complete(is_open(port))
	yield port
	loop.run_until_complete(p.kill())

@pytest.mark.run_loop
async def test_onewire_real(loop,owserver):
	ow = OnewireServer("127.0.0.1",owserver, loop=loop)
	res = await ow.dir('uncached')
	assert "bus.0" in res
	assert "simultaneous" in res
	for p in res:
		if p.startswith("bus."):
			res2 = await ow.dir(p)
			for q in res2:
				if q.startswith("10."):
					r = await ow.dir('uncached',p,q)
					logger.debug(r)
					r = await ow.read(p,q,"temperature")
					assert float(r) == 1.6 # which hopefully will stay stable
					await ow.write(p,q,"temphigh", data="99")
	await ow.close()

@pytest.mark.run_loop
async def test_onewire_fake(loop):
	from etcd_tree import client
	from . import cfg
	amqt = -1
	t = await client(cfg, loop=loop)
	tr = await t.tree("/bus/onewire")
	td = await t.tree("/device/onewire")
	u = Unit("test.moat.onewire.client", cfg['config'], loop=loop)
	@u.register_alert("test.fake.temperature", call_conv=CC_DATA)
	def get_temp(val):
		nonlocal amqt
		amqt = val
	await u.start()

	with suppress(etcd.EtcdKeyNotFound):
		await t.delete('/task/fake/onewire/scan/:task', recursive=True)
	with suppress(etcd.EtcdKeyNotFound):
		await t.delete('/task/fake/onewire/run/:task', recursive=True)

	try:
		with mock.patch("moat.ext.onewire.task.OnewireServer", new=FakeBus(loop)) as fb, \
			mock.patch("moat.ext.onewire.task.trigger_hook", new=Trigger(loop)) as fs:
			mp = mock.patch("moat.ext.onewire.task.DEV_COUNT", new=1)
			mp.__enter__()

			# Set up the whole thing
			m = MoatTest(loop=loop)
			r = await m.parse("-vvvc test.cfg mod init moat.ext.onewire")
			assert r == 0, r
			try:
				await m.parse("-vvvc test.cfg bus 1wire server delete faker")
			except etcd.EtcdKeyNotFound:
				pass
			r = await m.parse("-vvvc test.cfg bus 1wire server add faker foobar.invalid - A nice fake 1wire bus")
			assert r == 0, r
			r = await m.parse("-vvvc test.cfg task add fake/onewire/run onewire/run server=faker delay=999 update_delay=0.2 Run the fake bus")
			assert r == 0, r
			r = await m.parse("-vvvc test.cfg task add fake/onewire/scan onewire/scan server=faker Scan the fake bus")
			assert r == 0, r
			r = await m.parse("-vvvc test.cfg task param fake/onewire/run restart=0 retry=0")
			assert r == 0, r
			r = await m.parse("-vvvc test.cfg task param fake/onewire/scan restart=0 retry=0")
			assert r == 0, r
			logger.debug("TC A")

			m = MoatTest(loop=loop)
			r = await m.parse("-vvvc test.cfg run -g fake/onewire/scan")
			assert r == 0, r
			logger.debug("TC A2")

			# Start the bus runner
			m = MoatTest(loop=loop)
			f = m.parse("-vvvc test.cfg run -g fake/onewire/run")
			f = asyncio.ensure_future(f,loop=loop)
			logger.debug("TC A3")

			# give it some time to settle (lots of new entries)
			await fs.step(f)
			await asyncio.sleep(1.5,loop=loop)
			await fs.step(f)
			logger.debug("TC B")

			# temperature device found, bus scan active
			async def mod_a():
				await td.wait()
				await tr.wait()
				assert td['10']['001001001001'][':dev']
				await td['10']['001001001001'][':dev']['input']['temperature'].set('alert','test.fake.temperature')
				await td['05']['010101010101'][':dev']['output']['pin'].set('rpc','test.fake.pin')
				assert tr['faker']['bus']['bus.42 1f.123123123123 aux']['devices']['10']['001001001001'] == '0'
				assert int(fb.bus_aux['simultaneous']['temperature']) == 1
			await fs.step(f,mod_a)
			logger.debug("TC C")
			await fs.step(f)
			await asyncio.sleep(2.5,loop=loop)
			await fs.step(f)
			logger.debug("TC D")

			# we should have a value by now
			async def mod_a2():
				await td.wait()
				assert float(td['10']['001001001001'][':dev']['input']['temperature']['value']) == 12.5, \
					td['10']['001001001001'][':dev']['input']['temperature']['value']
				assert td['05']['010101010101'][':dev']['input']['pin']['value'] == '0', \
					 td['05']['010101010101'][':dev']['input']['pin']['value']
			await fs.step(f,mod_a2)
			logger.debug("TC E")
			assert amqt == 12.5, amqt
			await u.rpc('test.fake.pin',1)

			# now unplug the sensor
			async def mod_x():
				del fb.bus_aux['10.001001001001']
			await fs.step(f,mod_x)
			logger.debug("TC F")

			m2 = MoatTest(loop=loop)
			r = await m2.parse("-vvvc test.cfg run -g fake/onewire/scan")
			assert r == 0, r
			del m2

			logger.debug("TC G")
			# watch it vanish
			async def mod_b():
				assert tr['faker']['bus']['bus.42 1f.123123123123 aux']['devices']['10']['001001001001'] == '1'
			await fs.step(f,mod_b)
			logger.debug("TC H")

			for x in range(3):
				m2 = MoatTest(loop=loop)
				r = await m2.parse("-vvvc test.cfg run -g fake/onewire/scan")
				assert r == 0, r
				del m2
			await asyncio.sleep(1.5,loop=loop)
			await fs.step(f)
			logger.debug("TC I")
			async def mod_c():
				assert td['05']['010101010101'][':dev']['input']['pin']['value'] == '1', \
					 td['05']['010101010101'][':dev']['input']['pin']['value']
				with pytest.raises(KeyError):
					tr['faker']['bus']['bus.42 1f.123123123123 aux']['devices']['10']['001001001001']
				with pytest.raises(KeyError):
					td['10']['001001001001'][':dev']['path']

				# also, nobody scanned the main bus yet
				with pytest.raises(KeyError):
					fb.bus['simultaneous']['temperature']

				# it's gone, so heat it up and plug it into the main bus
				fb.temp['temperature'] = 42.25
				fb.bus['10.001001001001'] = fb.temp
				# and prepare to check that the scanner doesn't any more
				fb.bus_aux['simultaneous']['temperature'] = 0
			await fs.step(f,mod_c)
			logger.debug("TC J")

			m2 = MoatTest(loop=loop)
			r = await m.parse("-vvvc test.cfg run -g fake/onewire/scan")
			assert r == 0, r

			logger.debug("TC K")
			await fs.step(f)
			await asyncio.sleep(2.5,loop=loop)
			await fs.step(f)
			logger.debug("TC L")

			# we're scanning the main bus now
			async def mod_s():
				await td.wait()
				await tr.wait()
				assert td['10']['001001001001'][':dev']['path']
				assert tr['faker']['bus']['bus.42']['devices']['10']['001001001001'] == '0'

				assert int(fb.bus['simultaneous']['temperature']) == 1
				assert int(fb.bus_aux['simultaneous']['temperature']) == 0
			await fs.step(f,mod_s)
			logger.debug("TC M")
			await fs.step(f)
			await asyncio.sleep(4.5,loop=loop)
			await fs.step(f)
			logger.debug("TC N")
			async def mod_a3():
				await td.wait()
				assert float(td['10']['001001001001'][':dev']['input']['temperature']['value']) == 42.25, \
					td['10']['001001001001'][':dev']['input']['temperature']['value']
			await fs.step(f,mod_a3)
			logger.debug("TC O")
			assert amqt == 42.25, amqt

			# More to come. For now, shut down.
			await fs.step(f,True)
			logger.debug("TC P")
			r = await f
			assert r == 0, r
			logger.debug("TC Z")
	finally:
		await u.stop()

