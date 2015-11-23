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
from moat.proto.onewire import OnewireProtocol, OnewireDir,OnewireRead,OnewireWrite

from . import ProcessHelper, is_open

import logging
logger = logging.getLogger(__name__)

@pytest.yield_fixture
def owserver(loop,unused_tcp_port):
	port = unused_tcp_port
	p = ProcessHelper("owserver", "--foreground", "-p", port, "--tester=10", "--error_level", 5, "--error_print", 2, loop=loop)
	loop.run_until_complete(p.start())
	loop.run_until_complete(is_open(port))
	yield port
	loop.run_until_complete(p.kill())

@pytest.mark.run_loop
async def test_onewire_dir(loop,owserver):
	c = ProtocolClient(OnewireProtocol, "127.0.0.1",owserver, loop=loop)
	owd = OnewireDir(conn=c, loop=loop)
	owr = OnewireRead(conn=c, loop=loop)
	oww = OnewireWrite(conn=c, loop=loop)
	f = asyncio.Future(loop=loop)
	f.set_result(None)
	await f
	res = await owd.run()
	assert "bus.0" in res
	assert "simultaneous" in res
	for p in res:
		if p.startswith("bus."):
			res2 = await owd.run(p)
			for q in res2:
				if q.startswith("10."):
					r = await c.run(owd,p,q)
					logger.debug(r)
					r = await owr.run(p,q,"temperature")
					assert float(r) == 1.6 # which hopefully will stay stable
					await oww.run(p,q,"temphigh", data="99")

