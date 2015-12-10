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
import io
import sys
import logging

from . import ProcessHelper, MoatTest

def test_task(loop):
	m = MoatTest(loop=loop)
	r = m.parse("-vvvc test.cfg task def init moat.task.test")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = m.parse("-vvvc test.cfg task def list")
	assert r == 0, r
	assert m.in_stdout('test/sleep\t'), m.stdout_data
	assert m.in_stdout('test/error\t'), m.stdout_data
	
	m = MoatTest(loop=loop)
	r = m.parse("-vvvc test.cfg task def delete test/sleep")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = m.parse("-vvvc test.cfg task def list")
	assert r == 0, r
	assert not m.in_stdout('test/sleep\t'), m.stdout_data
	assert m.in_stdout('test/error\t'), m.stdout_data
	
	m = MoatTest(loop=loop)
	r = m.parse("-vvvc test.cfg task def init moat.task.test")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = m.parse("-vvvc test.cfg task def list")
	assert r == 0, r
	assert m.in_stdout('test/sleep\t'), m.stdout_data
	
	m = MoatTest(loop=loop)
	r = m.parse("-vvvc test.cfg task def param test/sleep ttl 11")
	assert r == 0, r
	assert m.stdout_data == "ttl=11 (new)\n", m.stdout_data

	m = MoatTest(loop=loop)
	r = m.parse("-vvvc test.cfg task def param test/sleep ttl")
	assert r == 0, r
	assert m.stdout_data == "11\n", m.stdout_data
	
	m = MoatTest(loop=loop)
	r = m.parse("-vvvc test.cfg task def param test/sleep ttl 10")
	assert r == 0, r
	assert m.stdout_data == "ttl=10 (was 11)\n", m.stdout_data
	
	m = MoatTest(loop=loop)
	r = m.parse("-vvvc test.cfg task def param test/sleep ttl")
	assert r == 0, r
	assert m.stdout_data == "10\n", m.stdout_data
	
	m = MoatTest(loop=loop)
	r = m.parse("-vvvc test.cfg task def param test/sleep")
	assert r == 0, r
	assert m.stdout_data == "ttl\t10\n", m.stdout_data
	
	m = MoatTest(loop=loop)
	r = m.parse("-vvvc test.cfg task def param")
	assert r == 0, r
	assert m.stdout_data == "test/sleep\tttl\t10\n", m.stdout_data
	
	
def test_test(loop):
	m = MoatTest(loop=loop)
	r = m.parse("-vvvc tests/empty.cfg test config")
	assert r == 0, r # internal defaults

	m = MoatTest(loop=loop)
	r = m.parse("-vvvc tests/empty.cfg test etcd")
	assert r > 0, r

	m = MoatTest(loop=loop)
	r = m.parse("-vvvc test.cfg test Kill me hardeL")
	assert r == 3, r

	m = MoatTest(loop=loop)
	r = m.parse("-vvvc test.cfg test Kill me hardeR")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = m.parse("-vvvc test.cfg test")
	assert r > 0, r

	m = MoatTest(loop=loop)
	r = m.parse("-vvvc test.cfg test -f")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = m.parse("-vvvc test.cfg test")
	assert r == 0, r

def test_dummy(loop):
	from moat.cmd.dummy import Command as C

	m = MoatTest(loop=loop)
	r = m.parse("")
	assert r == 1, r

	m = MoatTest(loop=loop)
	r = m.parse("dummy --help")
	assert not r, r
	assert m.in_stdout("\nAliases:")
	assert m.in_stdout("dummmy")

	m = MoatTest(loop=loop)
	r = m.parse("dummy foo")
	assert r == 1, r
	assert m.stdout_data == ""

	m = MoatTest(loop=loop)
	r = m.parse("dummy nope")
	assert r == 1, r
	assert m.stdout_data == ""

	m = MoatTest(loop=loop)
	r = m.parse("-q dummy")
	assert r == 0, r
	assert m.stdout_data == ""

	m = MoatTest(loop=loop)
	r = m.parse("dummy")
	assert r == 1, r
	assert m.in_stdout(C.foo[0])
	assert not m.in_stdout(C.foo[1])
	assert not m.in_stdout(C.foo[2])

	m = MoatTest(loop=loop)
	r = m.parse("-v dummy")
	assert r == 2, r
	assert m.in_stdout(C.foo[0])
	assert m.in_stdout(C.foo[1])
	assert not m.in_stdout(C.foo[2])

def test_show(loop):
	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg show --help")
	assert not r, r
	assert m.stdout_data.startswith("Usage: [MoaT options] show [command]\n")
	assert m.in_stdout("--help")

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg show foobarbaz")
	assert r == 1, r
	assert m.debug_log[-1].getMessage() == "Unknown command 'foobarbaz'.\n"

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg show config")
	assert r == 0, r
	assert m.in_stdout("\n    codec: _json\n")

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg -o config.bla.fasel=123 show config config.bla.fasel")
	assert r == 0, r
	m.assert_stdout("'123'\n")

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg show config config.bla.fasel")
	assert r == 3, r

def test_set(loop):
	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg set etcd -d one")

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg show etcd one")
	assert r > 0, r
	assert m.debug_log[-2].getMessage() == 'key not present: one'

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg set etcd one.two=three")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg set etcd one.two=threeandahalf")
	assert r > 0, r
	assert m.debug_log[-2].getMessage() == 'Entry exists: one.two'

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg show etcd one")
	assert r == 0, r
	assert m.in_stdout("{two: three}"), m.stdout_data

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg set etcd -a one=whatever")
	assert r == 0, r
	k = m.stdout_data.rstrip('\n')

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg show etcd one."+k)
	assert r == 0, r
	m.assert_stdout("whatever\n...\n")

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg show etcd one.two")
	assert r == 0, r
	m.assert_stdout("three\n...\n")

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg show etcd -m one.two")
	assert r == 0, r
	i = int(m.stdout_data)
	assert i > 0, r

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg set etcd -m %d one.two=four" % (i-1,))
	assert r > 0, r
	assert m.debug_log[-2].getMessage() == 'Bad modstamp: one.two'

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg set etcd -m %d one.two=four" % (i,))
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg show etcd one.two")
	assert r == 0, r
	m.assert_stdout("four\n...\n")

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg set etcd -p three -d one.two")
	assert r > 0, r
	assert m.debug_log[-2].getMessage() == 'Bad modstamp: one.two'

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg set etcd -p four -d one.two")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg set etcd -d one")
	assert r == 0, r

	m = MoatTest(loop=loop)
	r = m.parse("-c test.cfg show etcd one")
	assert r > 0, r

