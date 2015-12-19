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

from .base import Device

class NoAlarmHandler(RuntimeError):
	pass

#class SelectDevice(type(Device)):
#	def __new__(cls,name,bases,nmspc):
#		"""Grab the class for the actual device here"""
#		import pdb;pdb.set_trace()
#		p=nmspc['parent'].parent
#		try:
#			cls = globals()['Onewire_'+p.name]
#		except KeyError:
#			pass
#		return super(SelectDevice,cls).__new__(cls,name,bases,nmspc)

class OnewireDevice(Device): #(, metaclass=SelectDevice):
	prefix = "onewire"
	description = "Something hanging off 1wire"
	inputs = {}
	outputs = {}
	_inited = False

	def __new__(cls,*a,parent=None,**k):
		try:
			cls = globals()['Onewire_'+parent.parent.name.upper()]
		except KeyError:
			pass
		return super(OnewireDevice,cls).__new__(cls)

#	def __init__(self,*a,**k):
#		super().__init__(*a,**k)
#		import pdb;pdb.set_trace()
#		self.dev = self.env.srv.at(self.parent.parent.name,self.parent.name)

	def has_update(self):
		super().has_update()
		if not self._inited:
			d = {'inputs':{},'outputs':{}}
			for k,v in self.inputs.items():
				d['inputs'][k] = {'type':v}
			for k,v in self.outputs.items():
				d['outputs'][k] = {'type':v}
			for k,v in d.items():
				self[k] = v
			self._inited = True

	@classmethod
	def types(cls, types):
		"""Override to get your subtypes registered with etcd_tree"""
		pass

	async def has_alarm(self):
		raise NoAlarmHandler(self)
	
	def scan_for(self, what):
		return None
	
	async def reading(self,what,value):
		await self['inputs'][what].set('value',value)

class Onewire_F0(OnewireDevice):
	description = "MoaT device"

	def scan_for(self,what):
		if what == "alarm":
			return 0.1
		return super().scan_for(what)

	async def has_alarm(self):
		reasons = await self.dev.read("alarm/sources")
		if not reasons:
			return
		for r in reasons.split(','):
			logger.warn("MoaT alarm on %s: no idea how to read '%s'",self.path,r)
		
class Onewire_10(OnewireDevice):
	description = "temperature sensor"
	inputs = {"temperature":'float'}

	async def has_alarm(self):
		# Duh.
		t = float(strip(await self.dev.read("temperature")))
		await self.dev.write("templow",int(t-0.5))
		await self.dev.write("temphigh",int(t+1.5))
		await self.reading("temperature",t)

	def scan_for(self, what):
		if what == "temperature":
			try:
				return float(self['attr']['scan_freq'])
			except KeyError:
				return 60
