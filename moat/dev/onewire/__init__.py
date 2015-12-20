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
from etcd_tree.node import mtFloat,mtInteger,mtString
from time import time

from ..base import Device

class NoAlarmHandler(RuntimeError):
	pass

value_types = {
	'float': mtFloat,
	'int': mtInteger,
}
device_types = {} # filled later

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
		"""Find the class for this device."""
		if not device_types:
			from moat.script.util import objects
			for typ in objects(__name__,OnewireDevice):
				fam = typ.family
				if isinstance(fam,str):
					device_types[fam] = typ
				else:
					for f in fam:
						device_types[f] = typ

		cls = device_types.get(parent.parent.name.upper(), cls)
		return super(OnewireDevice,cls).__new__(cls)

	def has_update(self):
		super().has_update()
		if not self._inited:
			path = self.get('path','')
			if path:
				srv,path = path.split(' ',1)
				assert self.env.srv_name == srv
				self.srv = self.env.srv.at('uncached').at(*path.split(' ')).at(self.parent.parent.name+'.'+self.parent.name)
			else:
				self.srv = None
			d = {'input':{},'output':{}}
			for k,v in self.inputs.items():
				d['input'][k] = {'type':v}
			for k,v in self.outputs.items():
				d['output'][k] = {'type':v}
			for k,v in d.items():
				self[k] = v
			self._inited = True

	@classmethod
	def types(cls, types):
		"""\
			Register value types with etcd_tree.
			Override to add your own categories; add to your
			inputs{}/outputs{} for atomic values"""

		types.register('input','*','timestamp', cls=mtFloat)
		types.register('output','*','timestamp', cls=mtFloat)
		for k,v in self.inputs.items():
			v = value_types.get(v,mtValue)
			types.register('input',k,'value', cls=v)
		for k,v in self.outputs.items():
			v = value_types.get(v,mtValue)
			types.register('output',k,'value', cls=v)
		pass

	async def has_alarm(self):
		raise NoAlarmHandler(self)
	
	def scan_for(self, what):
		return None
	
	async def reading(self,what,value, timestamp=None):
		if timestamp is None:
			timestamp = time()
		elif self['input'][what].get('timestamp',0) > timestamp:
			# a value from the past gets ignored
			return
		await self['input'][what].set('value',value)
		await self['input'][what].set('timestamp',timestamp)

