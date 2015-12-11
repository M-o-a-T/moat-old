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

from . import ProcessHelper, is_open, MoatTest

import logging
logger = logging.getLogger(__name__)

class FakeBus:
	def __init__(self,h,p, loop=None):
		assert h == "foobar.invalid"
		assert p == 4304
		self.loop=loop

	async def dir(self,*p):
		if p == ('uncached',):
			return ("bus.42","foobar")
		if p == ('uncached','bus.42'):
			return ('alarm','simultaneous','1f.123123123123','10.001001001001')
		if p == ('uncached','bus.42','1f.123123123123','main'):
			return ('alarm','simultaneous','F0.004200420042')
		if p == ('uncached','bus.42','1f.123123123123','aux'):
			return ('alarm','simultaneous')
		raise NotImplementedError("I don't know what '%s' is" % repr(p)) # pragma: no cover

	async def read(self,*p):
		raise NotImplementedError("I don't know what to read at '%s'" % repr(p)) # pragma: no cover

	async def read(self,*p, data=None):
		raise NotImplementedError("I don't know how to write '%s' to '%s'" % (data,repr(p))) # pragma: no cover

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
	with mock.patch("moat.task.onewire.OnewireServer", new=FakeBus) as mo:
		m = MoatTest(loop=loop)
		r = await m.parse("-vvvc test.cfg task def init moat.task.onewire")
		assert r == 0, r
		try:
			await m.parse("-vvvc test.cfg bus 1wire server delete faker")
		except etcd.EtcdKeyNotFound:
			pass
		r = await m.parse("-vvvc test.cfg bus 1wire server add faker foobar.invalid - A nice fake 1wire bus")
		assert r == 0, r
		r = await m.parse("-vvvc test.cfg task add fake/onewire onewire/scan server=faker delay=0 Scan the fake bus")
		assert r == 0, r
		r = await m.parse("-vvvc test.cfg task param fake/onewire restart 0 retry 0")
		assert r == 0, r

		r = await m.parse("-vvvc test.cfg run -g fake/onewire")
		assert r == 0, r

