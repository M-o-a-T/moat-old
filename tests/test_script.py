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
import tempfile

from . import ProcessHelper, is_open, MoatTest
from moat.script.task import _task_reg

import logging
logger = logging.getLogger(__name__)

async def add_script(name,s,loop):
	m = MoatTest(loop=loop)
	await m.parse("moat -vvc test.cfg script delete test/%s" % (name,))
	m = MoatTest(loop=loop)
	await m.parse("moat -vvc test.cfg script def delete test/%s" % (name,))

	with tempfile.NamedTemporaryFile(prefix=name, suffix=".tmp") as tf:
		tf.write(s.encode("utf-8"))
		tf.flush()

		m = MoatTest(loop=loop)
		e = await m.parse("moat -vvc test.cfg script def add test/%s %s" % (name,tf.name))
		assert e == 0
	
	m = MoatTest(loop=loop)
	e = await m.parse("moat -vvc test.cfg script add test/%s test/%s" % (name,name))
	assert e == 0

async def dly(n,pred):
	while True:
		if pred():
			return
		logger.debug("DLY Again")
		n -= 0.5
		if n <= 0:
			break
		await asyncio.sleep(0.5, loop=loop)
	logger.debug("DLY Fail")
	raise RuntimeError("Predicate not taken")

async def run_script(name,loop):
	m = MoatTest(loop=loop)
	e = asyncio.ensure_future(m.parse("-vvvc test.cfg run -gS test/%s"%(name,)), loop=loop)
	return e

async def end_script(e):
	e.stop()
	e = await e
	assert e == 0

@pytest.mark.run_loop
async def test_script_basic(loop):
	#from etcd_tree import client
	#from . import cfg
	#t = await client(cfg, loop=loop)
	#td = await t.tree("/")

	s = """\
		moat.setup()
		assert "bus" in moat.root
		assert "meta" in moat.root

		did_it = True
		"""
	
	async def run(cmd):
		m9 = MoatTest(loop=loop)
		e = m9.parse(cmd)
		e = asyncio.ensure_future(e,loop=loop)
		r = await e
		return r

	await add_script("base",s,loop)
	j = await run_script("base")
	await dly(lambda: j.job.vars.get('did_it',False))
	await j.end_script()

