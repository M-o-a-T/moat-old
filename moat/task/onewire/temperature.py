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
from contextlib import suppress

from . import ScanTask,dev_re

import logging
logger = logging.getLogger(__name__)

class ScanTemperature(ScanTask):
	typ = "temperature"

	async def task_(self):
		warned = False
		if not len(self.parent['devices']['10']):
			return True # pragma: no cover

		await self.bus.write("simultaneous","temperature", data="1")

		with suppress(asyncio.TimeoutError):
			await asyncio.wait_for(self._trigger,timeout=1.5,loop=self.loop)
		for dev,b in list(self.parent['devices']['10'].items()):
			if b > 0:
				continue # pragma: no cover # timing dependant
			try:
				dev = self.env.devices['10'][dev][':dev']
				t = float(await dev.srv.read("temperature"))
			except Exception as exc:
				warned = True
				logger.exception("Reading %s: device '%s' triggered an error", self.name,dev)
			else:
				await dev.reading("temperature",t)

		return warned
