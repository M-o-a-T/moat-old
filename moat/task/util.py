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

from ..script.task import Task
from etcd_tree.node import EtcFloat

class Sleeper(Task):
	"""This task just waits for a configured amount of time before exiting.
		You can use it in a 'moat run -K' command to limit runtimes."""
	summary="""A simple delay"""
	taskdef="sleep"
	d = None
	f = None

	@classmethod
	def types(cls,tree):
		super().types(tree)
		tree.register("delay",cls=EtcFloat)
		
	def _timeout(self):
		if self.f is not None:
			self.f.set_result(None)
		if self.d is not None:
			logger.info('CANCEL 20 %s',self.d)
			self.d.cancel()

	async def task(self):
		t = time()
		if 'delay' not in self.config:
			await self.config.set('delay',10)

		while t+self.config['delay'] > time():
			self.t_updated = False
			self.f = asyncio.Future(loop=self.loop)
			self.d = self.loop.call_later(self.config['delay'], self._timeout)
			try:
				await self.f
			except asyncio.CancelledError:
				if self.t_updated:
					continue
				raise
			finally:
				self.f = None

	def cfg_changed(self):
		self.t_updated = True
		if self.d is not None:
			logger.info('CANCEL 21 %s',self.d)
			self.d.cancel()
		if self.f is not None:
			self.f.set_result(None)

