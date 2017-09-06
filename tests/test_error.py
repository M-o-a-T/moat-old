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
from etcd_tree import EtcDir

from moat.task.reg import REG,Reg
from moat.types.error import hasErrorDir
from moat.types import ERROR_DIR
from . import MoatTest

class ErrorTest(hasErrorDir,EtcDir):
	pass

from moat.types.etcd import MoatRoot
MoatRoot.register('test','*', cls=ErrorTest)

@pytest.mark.run_loop
async def test_main(loop):
	from . import cfg
	m = MoatTest(loop=loop)
	m.cfg = cfg
	t = await m._get_tree()
	try:
		try:
			tx = await t['test']
		except KeyError:
			pass
		else:
			await tx.delete(recursive=True)
		try:
			tx = await t['status']['error']['test']
		except KeyError:
			pass
		else:
			await tx.delete(recursive=True)
		
		e1 = await t.subdir("test","one", create=True)
		await e1.set_error("test","This is One")

		tx = t.lookup(ERROR_DIR)['test']
		assert len(tx) == 1, dict(tx.items())
		tp = list(tx.values())[0]
		assert tp['msg'] == "This is One",tx['msg']

		await e1.set_error("test","This is One too")
		assert tp['counter'] == 2

		await e1.clear_error("test")
		assert len(tx) == 0, dict(tx.items())

	finally:
		await m.finish()

