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
from moat.task import TASKSTATE
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
	td = await t.tree("/")
	u = Unit("test.moat.extern.client", amqp=cfg['config']['amqp'], loop=loop)
	@u.register_alert("test.fake.temperature", call_conv=CC_DATA)
	def get_temp(val):
		nonlocal amqt
		amqt = val
	await u.start()

	m = MoatTest(loop=loop)
	m.cfg = cfg
	await m.clean_ext("extern")

	e = f = None
	async def run(cmd):
		nonlocal e
		m9 = MoatTest(loop=loop)
		e = m9.parse(cmd)
		e = asyncio.ensure_future(e,loop=loop)
		r = await e
		e = None
		return r
	try:
		# Set up the whole thing
		m2 = MoatTest(loop=loop)
		r = await m2.parse("-vvvc test.cfg mod init moat.ext.extern")
		assert r == 0, r

		r = await run("-vvvc test.cfg dev extern add foo/bar int input/topic=test.foo.bar output/topic=set.foo.bar sync=false Test One")
		assert r == 0, r
		#r = await run("-vvvc test.cfg dev extern add foo/baz int input/topic=test.foo.baz input/ output/topic=set.foo.bar Test One")
		assert r == 0, r

		r = await run("-vvvc test.cfg run -qgootS moat/scan")
		assert r == 0, r
		r = await run("-vvvc test.cfg run -qgootS moat/scan/device")
		assert r == 0, r
		r = await run("-vvvc test.cfg run -qgootS moat/scan/device/extern")
		assert r == 0, r
		m2 = MoatTest(loop=loop)
		f = m2.parse("-vvvc test.cfg run -gS extern")
		f = asyncio.ensure_future(f,loop=loop)

		logger.debug("Waiting 1: create scan task")
		t1 = time()
		while True:
			try:
				await td.subdir('status','run','extern',TASKSTATE, create=False)
			except KeyError:
				pass
			else:
				logger.debug("Found 1")
				break

			await asyncio.sleep(0.1, loop=loop)
			if time()-t1 >= 30:
				raise RuntimeError("Condition 1")

		logger.debug("TC A")
		await asyncio.sleep(1, loop=loop)

		await u.alert('test.foo.bar',{'value':42})

		v = await td.lookup('device','extern','foo','bar',':dev')
		t1 = time()
		while True:
			try:
				val = v['value']
			except KeyError:
				pass
			else:
				logger.debug("Found 2")
				break

			if v.is_ready:
				await asyncio.sleep(0.1, loop=loop)
			else:
				await v.ready
			if time()-t1 >= 30:
				raise RuntimeError("Condition 2")

		assert val == '42', val
		tde = _task_reg[('extern',)]
		vr = await tde.tree.lookup('device','extern','foo','bar',':dev')
		assert vr['value'] == '42', vr['value']
		assert vr.value == 42, vr.value

		did_it = asyncio.Event(loop=loop)
		async def do_up(data):
			logger.debug("did_it %s",repr(data))
			assert data['value'] == 99
			await u.alert('test.foo.bar',{'value':98})
			did_it.set()
		await u.register_alert_async("set.foo.bar", do_up, call_conv=CC_DATA)
		await vr.set_value(99)
		await asyncio.wait_for(did_it.wait(),10, loop=loop)
		await vr.ready
		assert vr.value == 98, vr.value

#		async def do_up2(data):
#			import pdb;pdb.set_trace()
#			assert d['args'] == ['trigger','hello.foo.bar']
#			assert d['value'] == 97
#			await u.alert('test.foo.bar',{'value':96})
#			pass
#		await u.register_rpc_async("do.foo.bar", do_up2, call_conv=CC_DATA)

	finally:
		jj = (e,f)
		for j in jj:
			if j is None: continue
			if not j.done():
				j.cancel()
		for j in jj:
			if j is None: continue
			with suppress(asyncio.CancelledError):
				await j
		await u.stop()
		await td.close()
		await m.finish()
		t.close()

