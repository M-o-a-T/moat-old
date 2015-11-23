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

from . import ProcessHelper

@pytest.mark.run_loop
async def test_base(loop):
	p = ProcessHelper("sleep",1, loop=loop)
	t1 = time()
	await p.start()
	await p.wait()
	t2 = time()
	assert t2-t1 > 0.9
	assert t2-t1 < 1.2

@pytest.mark.run_loop
async def test_base_fd(loop):
	p = ProcessHelper("echo","Foo!", loop=loop)
	await p.start()
	await p.wait()
	assert p.fd[1] == b"Foo!\n"

@pytest.mark.run_loop
async def test_base_kill(loop):
	p = ProcessHelper("sleep",1, loop=loop)
	t1 = time()
	await p.start()
	await asyncio.sleep(0.1, loop=loop)
	await p.stop()
	t2 = time()
	assert t2-t1 < 0.3
