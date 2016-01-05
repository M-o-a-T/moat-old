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
from time import time

from .. import DEV
from ..base import Device

class NoAlarmHandler(RuntimeError):
	pass

value_types = {
	'float': EtcFloat,
	'int': EtcInteger,
}
_device_types = {} # filled later

def device_types():
	if not _device_types:
		from moat.script.util import objects
		for typ in objects(__name__,OnewireDevice):
			fam = typ.family
			if isinstance(fam,str):
				_device_types[fam] = typ
			else:
				for f in fam:
					_device_types[f] = typ
	return _device_types

class OnewireDevice(Device): #(, metaclass=SelectDevice):
	prefix = "onewire"
	name = "generic"
	description = "Something hanging off 1wire"
	_inited = False
	_cached_path = None

	def has_update(self):
		super().has_update()

		srvpath = self.get('path','')
		if self._cached_path is None or srvpath != self._cached_path:
			if srvpath != '':
				srv,path = srvpath.split(' ',1)
				assert self.env.srv_name == srv
				self.bus = self.env.srv.at('uncached').at(*path.split(' ')).at(self.parent.parent.name+'.'+self.parent.name)
				self.bus_cached = self.env.srv.at(*path.split(' ')).at(self.parent.parent.name+'.'+self.parent.name)
			else:
				self.bus = None
				self.bus_cached = None
			self._cached_path = srvpath

	@classmethod
	def dev_paths(cls):
		for k,cls in device_types().items():
			yield (k,'*',cls)
		yield ('*','*',OnewireDevice)

	def scan_for(self, what):
		return None
	
	async def has_alarm(self):
		raise NoAlarmHandler(self)
	
