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
import io
import sys
from contextlib import suppress
import aio_etcd as etcd

from moat.task import TASK

from . import ProcessHelper, MoatTest

import logging
logger = logging.getLogger(__name__)

@pytest.mark.run_loop
async def test_taskdef(loop):
	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg test -f")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task def init moat.task.test")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task def list")
	assert r == 0, r
	assert m.in_stdout('test/sleep\t'), m.stdout_data
	assert m.in_stdout('test/error\t'), m.stdout_data
	
	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task def delete test/sleep")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task def list")
	assert r == 0, r
	assert not m.in_stdout('test/sleep\t'), m.stdout_data
	assert m.in_stdout('test/error\t'), m.stdout_data
	
	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task def init moat.task.test")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task def list")
	assert r == 0, r
	assert m.in_stdout('test/sleep\t'), m.stdout_data
	
	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task def param test/sleep ttl=11")
	assert r == 0, r
	assert m.stdout_data == "ttl=11 (new)\n", m.stdout_data

	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task def param test/sleep ttl")
	assert r == 0, r
	assert m.stdout_data == "11\n", m.stdout_data
	
	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task def param test/sleep ttl retry")
	assert r == 0, r
	assert m.in_stdout("ttl\t11\n")
	assert m.in_stdout("retry\t-\n")
	
	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task def param test/sleep ttl=10")
	assert r == 0, r
	assert m.stdout_data == "ttl=10 (was 11)\n", m.stdout_data
	
	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task def param test/sleep ttl")
	assert r == 0, r
	assert m.stdout_data == "10\n", m.stdout_data
	
	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task def param test/sleep")
	assert r == 0, r
	assert m.stdout_data == "ttl\t10\n", m.stdout_data
	
	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task def param")
	assert r == 0, r
	assert m.stdout_data == "test/sleep\tttl\t10\n", m.stdout_data
	
@pytest.mark.run_loop
async def test_task(loop):
	from etcd_tree import client
	from . import cfg
	t = await client(cfg, loop=loop)
	with suppress(etcd.EtcdKeyNotFound):
		await t.delete('/task/fake/cmd/sleep/'+TASK, recursive=True)

	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg test -f")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task def init moat.task.test")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task def list")
	assert r == 0, r
	assert m.in_stdout('test/sleep\t'), m.stdout_data
	assert m.in_stdout('test/error\t'), m.stdout_data
	
	m = MoatTest(loop=loop)
	m2 = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task add fake/cmd/sleep test/sleep delay=2 Go to bed")
	assert r == 0, r
	r = await m.parse("-vvvc test.cfg task param fake/cmd/sleep restart=0 retry=0")
	assert r == 0, r
	rx = await m2.parse("-c test.cfg task state fake")
	assert rx == 0, rx

	r = await m.parse("-c test.cfg task list fake/cmd")
	assert m.in_stdout('fake/cmd/sleep\t'), m.stdout_data
	assert r == 0, r
	m = MoatTest(loop=loop)
	r = await m.parse("-vc test.cfg task list fake/cmd")
	assert m.stdout_data.startswith('*\tfake/cmd/sleep\n'), m.stdout_data
	assert r == 0, r
	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg task list fake/cmd/sleep")
	assert m.stdout_data.startswith('fake/cmd/sleep\t'), m.stdout_data
	assert r == 0, r
	m = MoatTest(loop=loop)
	r = await m.parse("-vc test.cfg task list fake/cmd/sleep")
	assert m.stdout_data.startswith('*\tfake/cmd/sleep\n'), m.stdout_data
	assert r == 0, r

	from moat.task import test as TT
	t = time()
	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg run -g fake/cmd/sleep")
	t2 = time()
	assert r == 0, r
	assert t2-t < 15 and t2-t > 2, (t,t2)
	assert TT.SLEEP == 2

	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task change fake/cmd/sleep delay=15")
	logger.info("A %s",time())
	assert r == 0, r

	TT.SLEEP = 0
	t = time()
	r = asyncio.ensure_future(m.parse("-vvvc test.cfg run -g fake/cmd/sleep"), loop=loop)
	while TT.SLEEP == 0:
		await asyncio.sleep(0.1,loop=loop)
		assert time()-t < 10
	assert not r.done(),repr(r)
	logger.info("B %s",time())
	m2 = MoatTest(loop=loop)
	rx = await m2.parse("-c test.cfg task state fake")
	logger.info("C %s",time())
	assert m2.in_stdout('fake/cmd/sleep\trun\t'), m2.stdout_data
	assert rx == 0, rx

	m2 = MoatTest(loop=loop)
	rx = await m2.parse("-vc test.cfg task state fake")
	logger.info("D %s",time())
	assert m2.in_stdout('*\tfake/cmd/sleep\n'), m2.stdout_data
	assert m2.in_stdout('state\trun\n'), m2.stdout_data
	assert rx == 0, rx

	m2 = MoatTest(loop=loop)
	logger.info("E %s",time())
	rx = await m2.parse("-vvc test.cfg task state fake")
	logger.info("F %s",time())
	assert m2.in_stdout('fake/cmd/sleep: {'), m2.stdout_data
	assert m2.in_stdout('state: run'), m2.stdout_data
	assert rx == 0, rx

	r = await r
	t2 = time()
	assert 15 < t2-t < 25, (t,t2)
	assert r == 0, r

@pytest.mark.run_loop
async def test_test(loop):
	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc tests/empty.cfg test config")
	assert r == 0, r # internal defaults

	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc tests/empty.cfg test etcd")
	assert r > 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg test Kill me hardeL")
	assert r == 3, r

	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg test Kill me hardeR")
	assert r == 0, r

	# now restore everything
	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg test")
	assert r > 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg test -f")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg test")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg task def init")
	assert r == 0, r

@pytest.mark.run_loop
async def test_dummy(loop):
	from moat.cmd.dummy import Command as C

	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg test -f")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("")
	assert r == 8, r

	m = MoatTest(loop=loop)
	r = await m.parse("dummy --help")
	assert not r, r
	# Alias support has been removed

	m = MoatTest(loop=loop)
	r = await m.parse("dummy foo")
	assert r == 1, r
	assert m.stdout_data == ""

	m = MoatTest(loop=loop)
	r = await m.parse("dummy nope")
	assert r == 1, r
	assert m.stdout_data == ""

	m = MoatTest(loop=loop)
	r = await m.parse("-q dummy")
	assert r == 0, r
	assert m.stdout_data == ""

	m = MoatTest(loop=loop)
	r = await m.parse("dummy")
	assert r == 1, r
	assert m.in_stdout(C.foo[0])
	assert not m.in_stdout(C.foo[1])
	assert not m.in_stdout(C.foo[2])

	m = MoatTest(loop=loop)
	r = await m.parse("-v dummy")
	assert r == 2, r
	assert m.in_stdout(C.foo[0])
	assert m.in_stdout(C.foo[1])
	assert not m.in_stdout(C.foo[2])

@pytest.mark.run_loop
async def test_show(loop):
	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg test -f")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg show --help")
	assert not r, r
	assert m.stdout_data.startswith("Usage: moat [global options …] show ‹command› [args …]\n")
	assert m.in_stdout("--help")

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg show foobarbaz")
	assert r == 3, r
	assert [ x for x in m.debug_log if x.getMessage() == "Unknown command: 'foobarbaz'" ], \
		[x.getMessage() for x in m.debug_log]

#	m = MoatTest(loop=loop)
#	r = await m.parse("-c test.cfg show config")
#	assert r == 0, r
#	assert m.in_stdout("\n    codec: _json\n"), m.stdout_data

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg -o config.bla.fasel=123 show config config.bla.fasel")
	assert r == 0, r
	m.assert_stdout("'123'\n")

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg show config config.bla.fasel")
	assert r == 3, r

@pytest.mark.run_loop
async def test_set(loop):
	m = MoatTest(loop=loop)
	r = await m.parse("-vvvc test.cfg test -f")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg set etcd -d one")

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg show etcd one")
	assert r > 0, r
	assert [ x for x in m.debug_log if x.getMessage() == "key not present: one" ], \
		[x.getMessage() for x in m.debug_log]

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg set etcd one.two=three")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg set etcd one.two=threeandahalf")
	assert r > 0, r
	assert [ x for x in m.debug_log if x.getMessage() == "Entry exists: one.two" ], \
		[x.getMessage() for x in m.debug_log]

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg set etcd -u one.two=threeandahalf")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg show etcd one")
	assert r == 0, r
	assert m.in_stdout("{two: threeandahalf}"), m.stdout_data

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg set etcd -a one=whatever")
	assert r == 0, r
	k = m.stdout_data.rstrip('\n')

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg show etcd one."+k)
	assert r == 0, r
	m.assert_stdout("whatever\n...\n")

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg show etcd one.two")
	assert r == 0, r
	m.assert_stdout("threeandahalf\n...\n")

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg show etcd -m one.two")
	assert r == 0, r
	i = int(m.stdout_data)
	assert i > 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg set etcd -m %d one.two=four" % (i-1,))
	assert r > 0, r
	assert [ x for x in m.debug_log if x.getMessage() == "Bad modstamp: one.two" ], \
		[x.getMessage() for x in m.debug_log]

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg set etcd -m %d one.two=four" % (i,))
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg show etcd one.two")
	assert r == 0, r
	m.assert_stdout("four\n...\n")

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg set etcd -p threeandahalf -d one.two")
	assert r > 0, r
	assert [ x for x in m.debug_log if x.getMessage() == "Bad modstamp: one.two" ], \
		[x.getMessage() for x in m.debug_log]

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg set etcd -p four -d one.two")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg set etcd -d one")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = await m.parse("-c test.cfg show etcd one")
	assert r > 0, r

