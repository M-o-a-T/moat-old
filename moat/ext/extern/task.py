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
from time import time
from weakref import WeakValueDictionary

from etcd_tree import EtcTypes, EtcFloat,EtcInteger,EtcValue,EtcDir
from aio_etcd import StopWatching

from contextlib import suppress
from moat.dev import DEV_DIR,DEV
from moat.bus import BUS_DIR
from moat.script.task import Task,TimeoutHandler
from moat.script.util import objects
from moat.task.device import DeviceMgr

import logging
logger = logging.getLogger(__name__)

class ExtHandler(DeviceMgr):
	"""\
		Manager task, handles interfacing with AMQP
		"""
	schema = {}
	taskdef = "extern/run"
	summary = "Interface to external AMQP-reachable devices"

	async def setup_vars(self):
		# onewire/NAME/scan/…
		self.srv_name = self.path[1]
		self.srv_tree = await self.tree.lookup(BUS_DIR+('onewire',self.srv_name))

		self.srv_data = await self.srv_tree['server']
		self.srv = OnewireServer(self.srv_data['host'],self.srv_data.get('port',None), loop=self.loop)
		self.devices = await self.tree.subdir(DEV_DIR+('onewire',))

	async def setup(self):
		"""\
			additional setup before DeviceMgr.task()
			"""
		await self.setup_vars()
		self.bus = self.srv.at('uncached')
		self.bus_cached = self.srv
		await super().setup()

