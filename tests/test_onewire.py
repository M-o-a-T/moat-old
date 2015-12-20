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
import mock
import etcd
from aioetcd import StopWatching

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
			}
		self.data = {
			"uncached": {
				"bus.42": self.bus,
				},
				"foobar":"whatever",
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
		logger.debug("BUSDIR %s %s",p,list(d.keys()))
		return d.keys()

	async def read(self,*p):
		d = self.data
		for s in p:
			d = d[s.lower()]
		assert not isinstance(d,dict)
		logger.debug("BUSREAD %s %s",p,d)
		return d

	async def write(self,*p, data=None):
		logger.debug("BUSWRITE %s %s",p,data)
		d = self.data
		for s in p[:-1]:
			d = d[s.lower()]
		d[p[-1].lower()] = data

class FakeSleep:
	# A fake implementation of a timer.
	# The task calls __call__ to set up its timeout and return a future.
	# The test calls step().
	# When both arrive, the future is triggered.
	# repeat.
	f = None
	g = None
	proc = None
	mod = None

	def __init__(self,loop):
		self.loop = loop

	async def __call__(self,loop,dly,proc):
		# called by the task when it wishes to create a timeout
		logger.debug("Enter: %s",proc)
		assert self.proc is None
		assert self.loop is loop
		if self.f is not None:
			self.f.set_result(False)
		if self.mod is not None:
			m,self.mod = self.mod,None
			await m()
		self.proc = proc
		return self
	def cancel(self):
		# called by the task when it wishes to cancel its timeout
		self.proc = None # pragma: no cover
		
	async def step(self, task, mod=False):
		"""\
			Trigger the fake timeout. @task is the task the timeout is
			running in so that we don't deadlock if it dies prematurely.
			@mod is a flag to signal StopWatching (if True), or a callback
			that's executed at the beginning of the next iteration.
			"""
		if self.proc is None:
			logger.debug("Wait: step %s",mod)
			self.f = asyncio.Future(loop=self.loop)
			await asyncio.wait((task,self.f), loop=self.loop,return_when=asyncio.FIRST_COMPLETED)
		logger.debug("Enter: step %s",mod)
		if not isinstance(mod,bool):
			self.mod = mod
		p,self.proc = self.proc,None
		self.f = None
		if mod is True:
			logger.debug("Kill: step %s",mod)
			p._timeout(StopWatching())
			await task
		else:
			logger.debug("Run: step %s",mod)
			if not task.done():
				p.trigger()
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
	t = await client(cfg, loop=loop)
	tr = await t.tree("/bus/onewire")
	td = await t.tree("/device/onewire")

	with mock.patch("moat.task.onewire.OnewireServer", new=FakeBus(loop)) as fb:
		with mock.patch("moat.task.onewire.Timer", new=FakeSleep(loop)) as fs:
			mp = mock.patch("moat.task.onewire.DEV_COUNT", new=1)
			mp.__enter__()

			# Set up the whole thing
			m = MoatTest(loop=loop)
			r = await m.parse("-vvvc test.cfg task def init moat.task.onewire")
			assert r == 0, r
			try:
				await m.parse("-vvvc test.cfg bus 1wire server delete faker")
			except etcd.EtcdKeyNotFound:
				pass
			r = await m.parse("-vvvc test.cfg bus 1wire server add faker foobar.invalid - A nice fake 1wire bus")
			assert r == 0, r
			r = await m.parse("-vvvc test.cfg task add fake/onewire/scan onewire/scan server=faker delay=999 update_delay=0.2 Scan the fake bus")
			assert r == 0, r
			r = await m.parse("-vvvc test.cfg task param fake/onewire/scan restart=0 retry=0")
			assert r == 0, r

			# Start the bus scanner
			f = m.parse("-vvvc test.cfg run -g fake/onewire")

			# give it some time to settle
			await fs.step(f)
			await asyncio.sleep(3.5,loop=loop)
			await fs.step(f)

			# temperature device found, bus scan active
			async def mod_a():
				await td.wait()
				await tr.wait()
				assert td['10']['001001001001'][':dev']
				assert tr['faker']['bus']['bus.42 1f.123123123123 aux']['devices']['10']['001001001001'] == '0'

				assert int(fb.bus_aux['simultaneous']['temperature']) == 1
			await fs.step(f,mod_a)
			await asyncio.sleep(2.0,loop=loop)
			await fs.step(f)

			# we should have a value by now
			async def mod_a2():
				await td.wait()
				assert float(td['10']['001001001001'][':dev']['input']['temperature']['value']) == 12.5
			await fs.step(f,mod_a2)

			# now unplug the sensor
			async def mod_x():
				del fb.bus_aux['10.001001001001']
			await fs.step(f,mod_x)

			# watch it vanish
			async def mod_b():
				assert tr['faker']['bus']['bus.42 1f.123123123123 aux']['devices']['10']['001001001001'] == '1'
			await fs.step(f,mod_b)
			await fs.step(f)
			async def mod_c():
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
			await fs.step(f)
			await asyncio.sleep(2.5,loop=loop)
			await fs.step(f)

			# we're scanning the main bus now
			async def mod_s():
				await td.wait()
				await tr.wait()
				assert td['10']['001001001001'][':dev']['path']
				assert tr['faker']['bus']['bus.42']['devices']['10']['001001001001'] == '0'

				assert int(fb.bus['simultaneous']['temperature']) == 1
				assert int(fb.bus_aux['simultaneous']['temperature']) == 0
			await fs.step(f,mod_s)
			await fs.step(f)
			await asyncio.sleep(4.5,loop=loop)
			await fs.step(f)
			async def mod_a3():
				await td.wait()
				assert float(td['10']['001001001001'][':dev']['input']['temperature']['value']) == 42.25, \
					td['10']['001001001001'][':dev']['input']['temperature']['value']
			await fs.step(f,mod_a3)

			# More to come. For now, shut down.
			await fs.step(f,True)
			r = await f
			assert r == 0, r

