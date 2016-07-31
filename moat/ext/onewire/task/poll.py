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

from moat.dev import DEV
from . import ScanTask,dev_re

import logging
logger = logging.getLogger(__name__)

class ScanPoll(ScanTask):
	typ = "poll"

	async def task_(self):
		for fam,d in self.parent['devices'].items():
			logger.debug("items %s %s",self,fam)
			for devid,b in (await d).items():
				try:
					logger.debug("get %s %s %s",self,fam,devid)
					dev = await self.devices[fam][devid][DEV]
					logger.debug("poll %s",dev)
					await dev.poll()
					logger.debug("poll_done %s",dev)
				except asyncio.CancelledError:
					raise
				except Exception:
					logger.exception("Poll error %s.%s", fam,devid)
					raise
		logger.debug("items end %s",self)

