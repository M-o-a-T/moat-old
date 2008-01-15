# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2008, Matthias Urlichs <matthias@urlichs.de>
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

from __future__ import division

"""\
This code implements basic commands to access FS20 switches.

"""

from homevent.module import Module
#from homevent.statement import AttributedStatement,Statement, main_words, \
#	ComplexStatement
#from homevent.check import Check,register_condition,unregister_condition
from homevent.run import simple_event
#from homevent.event import Event
#from homevent.context import Context
#from homevent.base import Name
from homevent.fs20 import recv_handler, PREFIX

#from twisted.internet import protocol,defer,reactor
#from twisted.protocols.basic import _PauseableMixin
#from twisted.python import failure

PREFIX_EM = 'e'

# 
#A1A2A3V1  	T11T12T13T141  	T21T22T23T241 T31T32T33T341  	F11F12F13F141  	F21F22F23F241  	F31F32F33F341 Q1Q2Q3Q41  	S1S2S3S41
#_0..7_V 	_____0.1°____ 	_____1°______ _____10°_____ 	_____0.1%____ 	_____1%______ 	_____10%_____
#
#e01:04 060901 030705 0A03
#       +19.6°  57.3%

def em_proc_thermo_hygro(ctx, data):
	if len(data) != 7:
		simple_event(ctx, "fs20","em","bad_length","thermo_hygro",len(data),"".join("%x"%x for x in data[1:]))
		return None
	temp = data[1]/10 + data[2] + data[3]*10
	if data[0] & 8: temp = -temp
	hum = data[4]/10 + data[5] + data[6]*10
	return {"temperature":temp, "humidity":hum}
em_proc_thermo_hygro.em_name = "thermo_hygro"

em_procs = [ None, # em_proc_thermo,
             em_proc_thermo_hygro,
             None, # em_proc_rain,
             None, # em_proc_wind,
             None, # em_proc_thermo_hygro_baro,
             None, # em_proc_light,
             None, # em_proc_pyrano,
             None, # em_proc_combined,
           ]

class em_handler(recv_handler):
	def dataReceived(self, ctx, data, handler=None, timedelta=None):
		if len(data) < 4:
			return

		xsum = ord(data[-2])
		qsum = ord(data[-1])
		data = tuple(ord(d) for d in data[:-2])
		xs=0; qs=xsum
		for d in data:
			xs ^= d
			qs += d
		if xs != xsum:
			simple_event(ctx, "fs20","em","checksum1",xs,xsum,"".join("%x" % x for x in data))
			return
		if (qs+5)&15 != qsum:
			simple_event(ctx, "fs20","em","checksum2",(qs+5)&15,qsum,"".join("%x" % x for x in data))
			return
		try:
			g = em_procs[data[0]]
			if not g:
				raise IndexError(data[0])
		except IndexError:
			simple_event(ctx, "fs20","unknown","em",data[0],"".join("%x"%x for x in data[1:]))
		else:
			r = g(ctx, data[1:])
			if r is not None:
				for m,n in r.iteritems():
					simple_event(ctx, "fs20","em",g.em_name, (data[1]&7)+1,m,n)


class fs20em(Module):
	"""\
		Basic fs20 EM reception.
		"""

	info = "Basic fs20 switches"

	def load(self):
		PREFIX[PREFIX_EM] = em_handler()
	
	def unload(self):
		del PREFIX[PREFIX_EM]
	
init = fs20em
