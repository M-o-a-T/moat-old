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

import os
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
async def test_main(loop):
	from etcd_tree import client
	from . import cfg
	amqt = -1
	t = await client(cfg, loop=loop)
	td = await t.tree("/")
	u = Unit("test.moat.web.client", amqp=cfg['config']['amqp'], loop=loop)
	port=39999+(os.getpid() % 25535)

	m = MoatTest(loop=loop)
	m.cfg = cfg
	await m.clean_ext("web", ('device','extern'))
	
	e = f = g = h = None
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
		r = await m2.parse("-vvvc test.cfg test web")
		assert r == 0, r

		r = await m2.parse("-vvvc test.cfg web def add float/temperature unit='°C' Temperatur")
		assert r == 0, r

		r = await run("-vvvc test.cfg dev extern add web/one float input/topic=test.web.one output/topic=set.web.one output/mode=async Test Web One")
		assert r == 0, r

		r = await run("-vvvc test.cfg web data add test/web/one float/temperature value=extern/web/one Web One")
		assert r == 0, r

		r = await run("-vvvc test.cfg web server add test/one port=%d Test Server One" % (port,))
		assert r == 0, r


		r = await run("-vvvc test.cfg run -qgootS moat/scan")
		assert r == 0, r
		r = await run("-vvvc test.cfg run -qgootS moat/scan/web")
		assert r == 0, r
		r = await run("-vvvc test.cfg run -qgootS moat/scan/web/server")
		assert r == 0, r
		r = await run("-vvvc test.cfg run -qgootS moat/scan/web/server/test")
		assert r == 0, r
		r = await run("-vvvc test.cfg run -qgootS moat/scan/web/server/test/one")
		assert r == 0, r
		r = await run("-vvvc test.cfg run -qgootS moat/scan/device/extern")
		assert r == 0, r
		m2 = MoatTest(loop=loop)
		g = m2.parse("-vvvc test.cfg run -gS extern")
		g = asyncio.ensure_future(g,loop=loop)

		m3 = MoatTest(loop=loop)
		h = m2.parse("-vvvc test.cfg run -gS web/test")
		h = asyncio.ensure_future(h,loop=loop)

		logger.debug("Waiting 1: create scan task")
		t1 = time()
		while True:
			try:
				r = await td.subdir('status','run','web','test','one',TASKSTATE, create=False)
				r['running']
				r = await td.subdir('status','run','extern',TASKSTATE, create=False)
				r['running']
			except KeyError:
				pass
			else:
				logger.debug("Found 1")
				break
			await asyncio.sleep(0.1, loop=loop)
			if time()-t1 >= 30:
				raise RuntimeError("Condition 1")
		await asyncio.sleep(1, loop=loop)
		await u.alert('test.web.one',{'value':19.5})

		m2 = MoatTest(loop=loop)
		f = m2.parse("-vvvc test.cfg web serve -b 127.0.0.1 --port=%d" % (port,))
		f = asyncio.ensure_future(f,loop=loop)

		logger.warn("Connect to http://127.0.0.1:%d/test" % (port,))
		await asyncio.sleep(100, loop=loop)

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
		await td.close()
		await m.finish()
		t.close()

