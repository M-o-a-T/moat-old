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
from weakref import WeakSet
from etcd_tree import EtcFloat,EtcString, ReloadRecursive

from . import TASK_DIR,TASKSCAN_DIR
from moat.script.task import Task

import logging
logger = logging.getLogger(__name__)

class DeviceMgr(Task):
	"""\
		This task runs some group of devices.

		When added at /task/WHATEVER/run, it registers
		itself as a manager to whatever .managed() returns
		(which needs to be a subclass of ManagedEtcDir).

		Supplement .setup() (and possibly .teardown()) if necessary.
		"""

	taskdef=None # must override
	summary="A Task which manages a group of devices"
	q = None

	async def setup(self):
		await super().setup()
		self.q = asyncio.Queue(loop=self.loop)
		self.amqp = self.cmd.root.amqp
		self._managed = await self.managed()
		if self._managed is not None:
			await self._managed.set_manager(self)

	async def teardown(self):
		if self._managed is not None:
			try:
				await self._managed.set_manager(None)
			except Exception:
				logger.exception("clearing manager")
		await super().teardown()

	async def managed(self):
		"""get the root of the tree we are managing"""
		raise NotImplementedError("Need to override %s.managed" % self.__class__.__name__)

	async def process(self, *cmd):
		"""\
			handle async processing.
			Extend by overriding.

			reg X: we manage X
			del X: un-manage X
			call X Y Z: await X(*Y,**Z)
			"""
		if cmd[0] == 'reg':
			await cmd[1].set_managed(self)
		elif cmd[0] == 'del':
			await cmd[1].set_unmanaged()
		elif cmd[0] == 'call':
			await cmd[1](*(cmd[2]),**(cmd[3]))
		else:
			logger.error("Bad command: %s",repr(cmd))

	async def task(self):
		try:
			while True:
				cmd = await self.q.get()
				if cmd is None:
					break
				await self.process(*cmd)
		except asyncio.CancelledError:
			raise
		except BaseException as exc:
			logger.exception("Duh?")
			raise

	def call_async(self, proc,*a,**k):
		self.q.put_nowait(('call',proc,a,k))
	def add_device(self, dev):
		self.q.put_nowait(('reg',dev))
	def drop_device(self, dev):
		self.q.put_nowait(('del',dev))

