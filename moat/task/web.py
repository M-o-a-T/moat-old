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
from moat.task.device import DeviceMgr
from moat.web import WEBDATA_DIR,WEBDATA, WEBSERVER_DIR,WEBSERVER

import logging
logger = logging.getLogger(__name__)

class WebServer(DeviceMgr):
	"""\
		This task runs the web server.
		"""

	taskdef="web/serve"
	summary="A Task which runs the web server"
	schema = {}

	app = None
	cfg = None
	cfg_mon = None

	async def setup(self):
		await super().setup()
		try:
			self.cfg = await self.tree.lookup(WEBSERVER_DIR+self.path[1:], name=WEBSERVER)
		except KeyError:
			raise RuntimeError("There is no configuration for this server.")

		self.cfg_mon = self.cfg.add_monitor(self.queue_reload)
		self.cfg.force_updated()

	def queue_reload(self, x=None):
		if x.is_new is None:
			self.cancel()
		else:
			self.q.put_nowait(("reload",))

	async def managed(self):
		return None

	async def process(self, *cmd):
		if cmd[0] == "reload":
			from moat.web.app import App
			if self.app is None:
				self.app = App(self)
				self.app.tree = await self.cmd.root._get_tree()
				await self.app.start(self.cfg.get('addr','127.0.0.1'), self.cfg.get('port',8080), self.cfg.get('default','default'))
			else:
				await self.app.change(self.cfg.get('addr','127.0.0.1'), self.cfg.get('port',8080), self.cfg.get('default','default'))
		else:
			await super().process(*cmd)

	async def teardown(self):
		if self.cfg_mon is not None:
			self.cfg_mon.cancel()
			self.cfg_mon = None
		if self.app is not None:
			try:
				await self.app.stop()
			except Exception as exc:
				logger.exception("stop web server")
			self.app = None
		await super().teardown()

