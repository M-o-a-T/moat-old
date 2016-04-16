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

import logging
logger = logging.getLogger(__name__)
from etcd_tree.node import EtcFloat,EtcInteger,EtcString

from . import OnewireDevice

class Onewire_2405(OnewireDevice):
	name = "pio"
	description = "one-bit I/O"
	output = {"pin":'bool'}
	input = {"pin":'bool'}
	family = "05"

	async def poll(self):
		# Duh.
		v = bool(int(await self.bus.read("sensed")))
		await self.reading("pin",v)

	async def read(self,what):
		"""Read the PIO pin."""
		assert what == "pin"
		return bool(int(await self.bus.read("sensed")))

	async def write(self,what, value):
		"""\
			Set the PIO pin.
			Inverse logic since the PIO is a pull-down,
			so 'true' means high which means writing a logic zero.
			"""
		assert what == "pin"
		await self.bus.write("PIO", data=('0' if value else '1'))

	def scan_for(self, what):
		if what == "poll":
			try:
				return float(self['attr']['poll_freq'])
			except KeyError:
				return 60
		return super().scan_for(what)
