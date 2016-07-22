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
from contextlib import suppress

from moat.dev import DEV
from . import ScanTask,dev_re

import logging
logger = logging.getLogger(__name__)

class ScanTemperature(ScanTask):
	typ = "temperature"

	async def task_(self):
		warned = False
		try:
			dev_10 = await self.parent['devices']['10']
		except KeyError:
			return True # pragma: no cover
		if not len(dev_10):
			return True # pragma: no cover

		await self.bus_cached.write("simultaneous","temperature", data="1")

		self.delay(1.5)
		for dev,b in list(dev_10.items()):
			if b.value > 0:
				continue # pragma: no cover # timing dependant
			d = None
			try:
				d = await self.devices['10'][dev][DEV]
				t = float(await self.bus_cached.read("10."+dev, "temperature"))
			except Exception as exc:
				warned = True
				logger.exception("Reading %s: device '%s' triggered an error", dev,d)
			else:
				await d.reading("temperature",t)

		return warned
