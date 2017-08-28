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
import gc
from time import time
from moat.task.reg import REG,Reg

from . import ProcessHelper

class foo:
	pass
foo = foo()

@pytest.mark.run_loop
async def test_reg(loop):
	class checker:
		def __init__(self, x):
			self.x = x
		def alloc(self):
			return foo
		def free(self, x):
			assert x is foo
			self.x[0]+=1

	REG(checker,"hey","alloc","free")
	r = Reg()
	x = [0]
	c = checker(x)
	await r.hey(c)
	await r.free()
	assert x[0] == 1

@pytest.mark.run_loop
async def test_free(loop):
	class checker:
		def __init__(self, x):
			self.x = x
		def alloc(self):
			return foo
		def free(self,x):
			assert x is foo
			self.x[0]+=1

	REG(checker,"hez","alloc","free")
	r = Reg()
	x = [0]
	c = checker(x)
	u = await r.hez(c)
	await u.release()
	assert x[0] == 1
	await r.free()
	assert x[0] == 1

@pytest.mark.run_loop
async def test_weak(loop):
	class dead:
		pass
	class checker:
		def __init__(self, x):
			self.x = x
		def alloc(self):
			return dead()
		def free(self,x): # should never be called
			self.x[0]+=1

	REG(checker,"hex","alloc","free")
	r = Reg()
	x = [0]
	c = checker(x)
	u = await r.hex(c)
	c = None
	gc.collect()
	await u.release()
	assert x[0] == 0
	await r.free()
	assert x[0] == 0

@pytest.mark.run_loop
async def test_task(loop):
	async def chk(x):
		x[0] += 2
		pass

	r = Reg()
	x = [0]
	cx = chk(x)
	t = r.task(cx)
	assert t.moat_reg is r
	await t
	assert x[0] == 2
