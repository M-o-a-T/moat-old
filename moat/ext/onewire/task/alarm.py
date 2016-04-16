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

from moat.dev import DEV
from . import ScanTask,dev_re

import logging
logger = logging.getLogger(__name__)

class ScanAlarm(ScanTask):
	typ = "alarm"

	async def task_(self):
		warned = False
		for dev in await self.bus.dir('alarm'):
			m = dev_re.match(dev)
			if m:
				try:
					d = await self.env.devices[m.group(1).lower()][m.group(2).lower()][DEV]
					await d.has_alarm()
				except KeyError:
					warned = True
					logger.warn("Scanning %s: device '%s' not found", self.name,dev)
				except NoAlarmHandler:
					warned = True
					logger.warn("Scanning %s: device '%s' does not have an alarm handler", self.name,dev)
				except Exception:
					warned = True
					logger.exception("Scanning %s: device '%s' triggered an error", self.name,dev)
			else:
				warned = True
				logger.warn("Scanning %s: no match for '%s'", self.name,dev)

			return warned
