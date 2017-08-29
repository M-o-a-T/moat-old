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
from etcd_tree import EtcFloat,EtcString, ReloadRecursive

from . import TASK_DIR,TASKSCAN_DIR
from moat.script.task import Task

import logging
logger = logging.getLogger(__name__)

class WebServer(DeviceMgr):
	"""\
		This task runs the web server.
		"""

	taskdef="web/server"
	summary="A Task which runs the web server"
	schema = {}

	async def setup(self):
		import pdb;pdb.set_trace()
		if len(self.path) != 2 or self.path[0] != self.cmd.root.app or self.path[1] != 'web':
			raise RuntimeError("You cannot run a web server globally (%s vs. %s)",
				str(self.path),repr(self.cmd.root.app))
		await super().setup()
		try:
			self.cfg = await self.tree.lookup(WEBDATA_DIR+(WEBCONFIG,self.cmd.root.app))
		except KeyError:
			raise RuntimeError("There is no configuration for this server.")

		from moat.web.app import App
		self.app = App(self)
		self.app.tree = await self.root._get_tree()
		await self.app.start(self.cfg.get('host','127.0.0.1', self.get('port',8080), self.cfg.get('default','default'))

	async def process(self, *cmd):
		await super().process(*cmd)

	async def teardown(self):
		if self.app is not None:
			try:
				await self.app.stop()
			except Exception as exc:
				logger.exception("stop web server")
		await super().teardown()
