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
import pytest
from time import time
from moat.proto import ProtocolClient
from qbroker.unit import Unit,CC_DATA
from moat.ext.onewire.proto import OnewireServer
from moat.task import TASK
import mock
import aio_etcd as etcd
from contextlib import suppress

from . import ProcessHelper, is_open, MoatTest
from moat.script.task import _task_reg

import logging
logger = logging.getLogger(__name__)

_logged = {} # debug: only log changed directories

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
		k = sorted(d.keys())
		if _logged.get(p,['nope']) != k:
			logger.debug("BUS.DIR %s %s",p,k)
			_logged[p] = k
		return d.keys()

	async def read(self,*p):
		d = self.data
		try:
			for s in p:
				d = d[s.lower()]
		except KeyError as err:
			raise KeyError((self,p)) from err
		assert not isinstance(d,dict)
		logger.debug("BUS.READ %s %s",p,d)
		return d

	async def write(self,*p, data=None):
		logger.debug("BUS.WRITE %s %s",p,data)
		d = self.data
		try:
			for s in p[:-1]:
				d = d[s.lower()]
		except KeyError as err:
			raise KeyError((self,p)) from err
		d[p[-1].lower()] = data

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
	u = Unit("test.moat.onewire.client", amqp=cfg['config']['amqp'], loop=loop)
	@u.register_alert("test.fake.temperature", call_conv=CC_DATA)
	def get_temp(val):
		nonlocal amqt
		amqt = val
	await u.start()

	with suppress(etcd.EtcdKeyNotFound):
		await t.delete('/task/onewire/faker/scan/:task', recursive=True)
	with suppress(etcd.EtcdKeyNotFound):
		await t.delete('/task/onewire/faker/run/:task', recursive=True)
	with suppress(etcd.EtcdKeyNotFound):
		await t.delete('/device/onewire/05/010101010101', recursive=True)
	with suppress(etcd.EtcdKeyNotFound):
		await t.delete('/device/onewire/f0/004200420042', recursive=True)
	with suppress(etcd.EtcdKeyNotFound):
		await t.delete('/device/onewire/10/001001001001', recursive=True)
	with suppress(etcd.EtcdKeyNotFound):
		await t.delete('/device/onewire/1f/123123123123', recursive=True)

	e = f = g = h = None
	async def run(cmd):
		nonlocal e
		e = m.parse(cmd)
		e = asyncio.ensure_future(e,loop=loop)
		r = await e
		e = None
		return r
	try:
		with mock.patch("moat.ext.onewire.task.OnewireServer", new=FakeBus(loop)) as fb, \
			mock.patch("moat.ext.onewire.task.DEV_COUNT", new=1) as mp:

			# Set up the whole thing
			m = MoatTest(loop=loop)
			r = await m.parse("-vvvc test.cfg mod init moat.ext.onewire")
			assert r == 0, r
			await m.parse("-vvvc test.cfg conn onewire delete faker")
			r = await m.parse("-vvvc test.cfg conn onewire add faker foobar.invalid - A nice fake 1wire bus")
			assert r == 0, r
			r = await run("-vvvc test.cfg run -qgootS moat/scan")
			assert r == 0, r
			r = await run("-vvvc test.cfg run -qgootS moat/scan/bus")
			assert r == 0, r
			mto = await t.tree("/task/onewire")

			f = m.parse("-vvvc test.cfg run -gS moat/scan/bus/onewire")
			f = asyncio.ensure_future(f,loop=loop)
			await asyncio.sleep(1, loop=loop)

			logger.debug("Waiting 1: create scan task")
			t1 = time()
			while True:
				try:
					await mto.subdir('faker','scan',TASK,'taskdef', create=False)
				except KeyError:
					pass
				else:
					logger.debug("Found 1")
					break

				await asyncio.sleep(0.1, loop=loop)
				if time()-t1 >= 30:
					raise RuntimeError("Condition 1")

			g = m.parse("-vvvc test.cfg run -gS onewire/faker/scan")
			g = asyncio.ensure_future(g,loop=loop)

			logger.debug("Waiting 2: main branch's alarm task")
			t1 = time()
			while True:
				try:
					await mto.subdir('faker','run','bus.42 1f.123123123123 main','alarm',TASK, create=False)
				except KeyError:
					pass
				else:
					logger.debug("Found 2")
					break

				if time()-t1 >= 120:
					raise RuntimeError("Condition 2")
				await asyncio.sleep(0.1, loop=loop)

			logger.debug("TC A")

			# Start the bus runner
			m = MoatTest(loop=loop)
			h = m.parse("-vvvc test.cfg run -gS onewire/faker/run")
			h = asyncio.ensure_future(h,loop=loop)
			logger.debug("TC A3")

			# get job entry
			logger.debug("Waiting 2a: temperature scanner")
			t1 = time()
			while True:
				if ('onewire','faker','run','bus.42 1f.123123123123 aux','temperature') in _task_reg and \
				   ('onewire','faker','run','bus.42','poll') in _task_reg:
					logger.debug("Found 2a")
					break
				if time()-t1 >= 10:
					raise RuntimeError("Condition 2a")
				await asyncio.sleep(0.1, loop=loop)

			await asyncio.sleep(0.2,loop=loop)
			fsp = _task_reg[('onewire','faker','run','bus.42','poll')].job
			fst = _task_reg[('onewire','faker','run','bus.42 1f.123123123123 aux','temperature')].job
			logger.debug("TC B1")
			await fsp._call_delay()
			logger.debug("TC B2")
			await fst._call_delay()
			logger.debug("TC B3")

			# temperature device found, bus scan active
			async def mod_a():
				logger.debug("Mod A start")
				await td.wait()
				await tr.wait()
				assert td['10']['001001001001'][':dev']
				await td['10']['001001001001'][':dev']['input']['temperature'].set('alert','test.fake.temperature')
				p = td['05']['010101010101'][':dev']['output']['pin'].set
				#import pdb;pdb.set_trace()
				await p('rpc','test.fake.pin')
				assert tr['faker']['bus']['bus.42 1f.123123123123 aux']['devices']['10']['001001001001'] == '0'
				assert int(fb.bus_aux['simultaneous']['temperature']) == 1
				logger.debug("Mod A end")
			logger.debug("Mod A hook")
			await fsp._call_delay()
			await fst._call_delay(mod_a)
			logger.debug("Mod A done")
			logger.debug("TC C")
			await asyncio.sleep(2.5,loop=loop)
			logger.debug("TC CA")
			await fsp._call_delay()
			logger.debug("TC CB")
			await fst._call_delay()
			logger.debug("TC D")

			# we should have a value by now
			async def mod_a2():
				logger.debug("Mod A2 start")
				await td.wait()
				assert float(td['10']['001001001001'][':dev']['input']['temperature']['value']) == 12.5, \
					td['10']['001001001001'][':dev']['input']['temperature']['value']
				assert td['05']['010101010101'][':dev']['input']['pin']['value'] == '0', \
					 td['05']['010101010101'][':dev']['input']['pin']['value']
				logger.debug("Mod A2 end")
			await fst._call_delay(mod_a2)
			logger.debug("TC E")
			assert amqt == 12.5, amqt

			assert not fb.bus['05.010101010101'].val
			await u.rpc('test.fake.pin',1)
			logger.debug("TC E2")
			assert fb.bus['05.010101010101'].val
			await fsp._call_delay()

			# now unplug the sensor
			async def mod_x():
				logger.debug("Mod X")
				del fb.bus_aux['10.001001001001']
			await fst._call_delay(mod_x)
			logger.debug("TC F")

			t1 = time()
			while True:
				if ('onewire','faker','scan','bus.42 1f.123123123123 aux') in _task_reg:
					break
				if time()-t1 >= 10:
					raise RuntimeError("Condition 2b")
				await asyncio.sleep(0.1, loop=loop)

			fst2 = _task_reg[('onewire','faker','scan','bus.42 1f.123123123123 aux')]
			await fst2._trigger()
			del fst2


			logger.debug("TC G")
			# watch it vanish
			async def mod_b():
				assert int(tr['faker']['bus']['bus.42 1f.123123123123 aux']['devices']['10'].get('001001001001','9'))
			await fst._call_delay(mod_b)
			logger.debug("TC H")

			fst2 = _task_reg[('onewire','faker','scan','bus.42 1f.123123123123 aux')]
			for x in range(10):
				logger.debug("TC H_")
				await fst2._trigger()
				await asyncio.sleep(0.5,loop=loop)
				try:
					tr['faker']['bus']['bus.42 1f.123123123123 aux']['devices']['10']['001001001001']
				except KeyError:
					break

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
			await fst._call_delay(mod_c)
			logger.debug("TC I")

			fst2 = _task_reg[('onewire','faker','scan','bus.42')]
			for x in range(15):
				await fst2._trigger()
				await asyncio.sleep(0.5,loop=loop)
				if ('onewire','faker','run','bus.42','temperature') in _task_reg:
					break
			fst2 = _task_reg[('onewire','faker','run','bus.42','temperature')].job
			await asyncio.sleep(0.5,loop=loop)
			await fst._call_delay()
			await fst2._call_delay()
			logger.debug("TC J")

			logger.debug("TC K")
			await fst2._call_delay()
			await asyncio.sleep(2.5,loop=loop)
			await fst2._call_delay()
			logger.debug("TC L")

			# we're scanning the main bus now
			async def mod_s():
				await td.wait()
				await tr.wait()
				assert td['10']['001001001001'][':dev']['path']
				assert tr['faker']['bus']['bus.42']['devices']['10']['001001001001'] == '0'

				assert int(fb.bus['simultaneous']['temperature']) == 1
				assert int(fb.bus_aux['simultaneous']['temperature']) == 0
			await fst2._call_delay(mod_s)
			logger.debug("TC M")
			await fst2._call_delay()
			await asyncio.sleep(4.5,loop=loop)
			await fst2._call_delay()
			logger.debug("TC N")
			async def mod_a3():
				await td.wait()
				assert float(td['10']['001001001001'][':dev']['input']['temperature']['value']) == 42.25, \
					td['10']['001001001001'][':dev']['input']['temperature']['value']
			await fst2._call_delay(mod_a3)
			logger.debug("TC O")
			assert amqt == 42.25, amqt

			# More to come.

	finally:
		jj = (e,f,g,h)
		for j in jj:
			if j is None: continue
			if not j.done():
				j.cancel()
		for j in jj:
			if j is None: continue
			with suppress(asyncio.CancelledError):
				await j
		await u.stop()

