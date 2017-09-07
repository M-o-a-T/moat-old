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

from etcd_tree import EtcString,EtcDir,EtcFloat,EtcInteger,EtcValue, ReloadRecursive
import aio_etcd as etcd
from time import time
from weakref import ref

from moat.types import TYPEDEF_DIR,TYPEDEF
from moat.dev import devices, DEV

import logging
logger = logging.getLogger(__name__)

__all__ = ('Bus','DeadBus')

def setup_bus_types(types):
	"""Register types for all devices."""
	for bus in buses():
		t = types.step(dev.prefix)
		for p in dev.dev_paths():
			t.register(p[:-1]).register(DEV, cls=p[-1])
	types.register('*', cls=DeadBus)

class MoatBuses(EtcDir):
	"""singleton for etcd /bus"""
	async def init(self):
		setup_bus_types(self)
		
		await super().init()

class BaseBus(EtcDir):
	"""\
		This is the parent class for buses MoaT uses.

		A Bus corresponds to a distinct way to communicate with an external
		entity (one KNX interface, one 1wire bus, …). Typically, several
		Devices are connected to a Bus entity.

		Buses are named /bus/TYPE/NAME.

		Devices may move between buses, thus they have their own hierarchy.

		"""

	prefix = "dummy"
	description = "Something that does nothing."

class DeadBus(BaseBus):
	"""\
		This bus has a broken prefix, the code to use it has been removed,
		or something else is Just Plain Wrong.
		"""
	name = 'dead'
	description = "Code not found"

class Bus(BaseBus):
	"""\
		This is the superclass for buses that actually work
		(or are supposed to work). Use this instead of BaseBus
		unless you have a very good reason not to.
		"""
	prefix = None
	description = "Override me"

