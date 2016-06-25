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
from weakref import WeakSet
from etcd_tree import EtcFloat,EtcString, ReloadRecursive
from dabroker.util import import_string

from . import TASK_DIR,TASKSCAN_DIR
from moat.script.task import Task

import logging
logger = logging.getLogger(__name__)


class DeviceMgr(Task):
	"""\
		This task runs some group of devices sharing a bus.

		When added at /task/WHATEVER/run, it registers
		itself as a manager to the /bus/WHATEVER node
		(which needs to be a ManagedEtcDir).

		This may be overridden if setup is required.
		"""

	taskdef="task/devices"
	summary="A Task which manages a group of devices"
	q = None

	async def task(self):
		self.q = asyncio.Queue()
		self.devices = WeakSet()
		self.amqp = self.cmd.root.amqp

		managed = await self.tree['bus']
		managed = await managed.lookup(*self.path[:-1])
		managed.manager = self

		try:
			while True:
				cmd = await self.q.get()
				if cmd is None:
					break
				if cmd[0] == 'reg':
					await cmd[1].set_managed(self)
				elif cmd[0] == 'upd':
					await cmd[1].update_managed()
				elif cmd[0] == 'call':
					await cmd[1](*(cmd[2]),**(cmd[3]))
				else:
					logger.error("Bad command: %s",repr(cmd))
		finally:
			del managed.manager

	def call_async(self, proc,*a,**k):
		self.q.put_nowait(('call',proc,a,k))
	def add_device(self, dev):
		self.q.put_nowait(('reg',dev))

