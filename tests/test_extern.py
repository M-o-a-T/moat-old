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
from moat.task import TASK
import mock
import aio_etcd as etcd
from contextlib import suppress

from . import ProcessHelper, is_open, MoatTest
from moat.script.task import _task_reg

import logging
logger = logging.getLogger(__name__)

_logged = {} # debug: only log changed directories

@pytest.mark.run_loop
async def test_extern_fake(loop):
	from etcd_tree import client
	from . import cfg
	amqt = -1
	t = await client(cfg, loop=loop)
	td = await t.tree("/device/extern")
	u = Unit("test.moat.extern.client", amqp=cfg['config']['amqp'], loop=loop)
	@u.register_alert("test.fake.temperature", call_conv=CC_DATA)
	def get_temp(val):
		nonlocal amqt
		amqt = val
	await u.start()

	with suppress(etcd.EtcdKeyNotFound):
		await t.delete('/task/extern/run/:task', recursive=True)

	e = f = g = h = None
	async def run(cmd):
		nonlocal e
		e = m.parse(cmd)
		e = asyncio.ensure_future(e,loop=loop)
		r = await e
		e = None
		return r
	try:
			# Set up the whole thing
			m = MoatTest(loop=loop)
			r = await m.parse("-vvvc test.cfg mod init moat.ext.extern")
			assert r == 0, r
			r = await run("-vvvc test.cfg run -qgootS moat/scan")
			assert r == 0, r
			r = await run("-vvvc test.cfg run -qgootS moat/scan/bus")
			assert r == 0, r
			mto = await t.tree("/task/extern")

			f = m.parse("-vvvc test.cfg run -gS moat/scan/bus/extern")
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

			g = m.parse("-vvvc test.cfg run -gS extern/faker/scan")
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
			h = m.parse("-vvvc test.cfg run -gS extern/faker/run")
			h = asyncio.ensure_future(h,loop=loop)
			logger.debug("TC A3")

			# get job entry
			logger.debug("Waiting 2a: temperature scanner")
			t1 = time()
			while True:
				if ('extern','faker','run','bus.42 1f.123123123123 aux','temperature') in _task_reg and \
				   ('extern','faker','run','bus.42','poll') in _task_reg:
					logger.debug("Found 2a")
					break
				if time()-t1 >= 10:
					raise RuntimeError("Condition 2a")
				await asyncio.sleep(0.1, loop=loop)

			await asyncio.sleep(0.2,loop=loop)
			fsp = _task_reg[('extern','faker','run','bus.42','poll')].job
			fst = _task_reg[('extern','faker','run','bus.42 1f.123123123123 aux','temperature')].job
			logger.debug("TC B1")
			await fsp._call_delay()
			logger.debug("TC B2")
			await fst._call_delay()
			logger.debug("TC B3")

			# temperature device found, bus scan active
			async def mod_a():
				logger.debug("Mod A start")
				await td.wait()
				assert td['10']['001001001001'][':dev']
				await td['10']['001001001001'][':dev']['input']['temperature'].set('alert','test.fake.temperature')
				p = td['05']['010101010101'][':dev']['output']['pin'].set
				#import pdb;pdb.set_trace()
				await p('rpc','test.fake.pin')
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
				if ('extern','faker','scan','bus.42 1f.123123123123 aux') in _task_reg:
					break
				if time()-t1 >= 10:
					raise RuntimeError("Condition 2b")
				await asyncio.sleep(0.1, loop=loop)

			fst2 = _task_reg[('extern','faker','scan','bus.42 1f.123123123123 aux')]
			await fst2._trigger()
			del fst2

			logger.debug("TC G")
			# watch it vanish
			async def mod_b():
				#assert int(tr['faker']['bus']['bus.42 1f.123123123123 aux']['devices']['10'].get('001001001001','9'))
				pass
			await fst._call_delay(mod_b)
			logger.debug("TC H")

			fst2 = _task_reg[('extern','faker','scan','bus.42 1f.123123123123 aux')]
			for x in range(10):
				logger.debug("TC H_")
				await fst2._trigger()
				await asyncio.sleep(0.5,loop=loop)
				try:
					# tr['faker']['bus']['bus.42 1f.123123123123 aux']['devices']['10']['001001001001']
					pass
				except KeyError:
					break

			async def mod_c():
				assert td['05']['010101010101'][':dev']['input']['pin']['value'] == '1', \
					 td['05']['010101010101'][':dev']['input']['pin']['value']
				#with pytest.raises(KeyError):
				#	tr['faker']['bus']['bus.42 1f.123123123123 aux']['devices']['10']['001001001001']
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

			fst2 = _task_reg[('extern','faker','scan','bus.42')]
			for x in range(15):
				await fst2._trigger()
				await asyncio.sleep(0.5,loop=loop)
				if ('extern','faker','run','bus.42','temperature') in _task_reg:
					break
			fst2 = _task_reg[('extern','faker','run','bus.42','temperature')].job
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
				assert td['10']['001001001001'][':dev']['path']
				#assert tr['faker']['bus']['bus.42']['devices']['10']['001001001001'] == '0'

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

			# drop the switch
			del fb.bus['1f.123123123123']

			fsb = _task_reg[('extern','faker','scan','bus.42')]
			t1 = time()
			while True:
				if int(tr['faker']['bus']['bus.42']['devices']['1f'].get('123123123123','9')) == 9:
					break
				if time()-t1 >= 10:
					raise RuntimeError("Condition 3b")
				await asyncio.sleep(0.1, loop=loop)
				await fsb._trigger()

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

