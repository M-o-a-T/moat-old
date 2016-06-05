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
from etcd_tree.node import EtcFloat,EtcInteger,EtcString, EtcDir
from time import time

from moat.bus.base import Bus
from moat.types.etcd import MoatBusBase, Subdirs

class OnewireBusBase(MoatBusBase):
	"""Directory for /bus/onewire"""
	@property
	def task_monitor(self):
		return Subdirs(self)
	def task_for_subdir(self,d):
		return "scan",

class OnewireBus(Bus):
	"""Directory for /bus/onewire/NAME"""
	prefix = "onewire"
	description = "A controller for 1wire"

	@property
	def task_monitor(self):
		#yield "add",("onewire","run"), ('onewire',self.name,'run'), {}
		yield "add",('onewire','scan'), ('onewire',self.name,'scan'), {}
		yield "scan",('bus','onewire',self.name,'bus'), {}

class OnewireBusSub(EtcDir):
	"""Directory for /bus/onewire/NAME/bus"""
	@property
	def task_monitor(self):
		return Subdirs(self)
	def task_for_subdir(self,d):
		return "scan",

class OnewireBusOne(EtcDir):
	"""Directory for /bus/onewire/NAME/bus/BUS"""
	@property
	def task_monitor(self):
		yield "add",('onewire','scan','bus'), ('onewire',self.path[2],'scan',self.name), {}
		yield "scan",('bus','onewire',self.path[2],'bus','devices'), {}
	def task_for_subdir(self,d):
		return "scan",

class OnewireBusDev(EtcDir):
	"""Directory for /bus/onewire/NAME/bus/BUS/devices"""
	@property
	def task_monitor(self):
		return Subdirs(self)
	def task_for_subdir(self,d):
		import pdb;pdb.set_trace()
		return "foof",

OnewireBusBase.register('*',cls=OnewireBus)
OnewireBus.register("server","host", cls=EtcString)
OnewireBus.register("server","port", cls=EtcInteger)
OnewireBus.register('bus', cls=OnewireBusSub)
OnewireBusSub.register('*', cls=OnewireBusOne)
OnewireBusOne.register('broken', cls=EtcInteger)
OnewireBusOne.register('devices', cls=OnewireBusDev)
OnewireBusDev.register('*','*', cls=EtcInteger)

