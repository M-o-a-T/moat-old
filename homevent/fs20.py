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
This module is the basis for processing FS20 datagrams.
"""

from homevent.event import Event
from homevent.run import simple_event
from homevent.context import Context

from time import time

PREFIX_FS20 = 'f'
PREFIX_EM = 'e'
PREFIX = 'ef' # all of them!
PREFIX_TIMESTAMP = 't'

groups = {}
handlers = []
default_handler = None

class WrongDatagram(TypeError):
	"""The datagram could not be recognized"""
	pass

def to_hc(code, _len=8):
	"""convert a number to an n-digit 1234 value"""
	sft = 2*(_len-1)
	res = 0
	if isinstance(code,basestring):
		code = int(code)
	while True:
		res = 10*res + (((code >> sft) & 3) + 1)
		if not sft: break
		sft = sft-2
	return res

def from_hc(code, _len=8):
	"""convert an-digit 1234 value to a number"""
	res = 0
	sft = 0
	if isinstance(code,basestring):
		code = int(code)
	assert len(str(code)) == _len, "wrong format: "+str(code)
	while code:
		c = code % 10
		assert c >= 1 and c <= 5, "wrong form: "+str(code)
		res += (c - 1) << sft
		sft += 2
		code = code // 10
	return res

def to_dev(code):
	return to_hc(code, _len=4)
def from_dev(code):
	return from_hc(code, _len=4)
		

def register_handler(h):
	global default_handler
	if h in handlers:
		raise RuntimeError("Handler already registered: %s" % (h,))
	handlers.append(h)
	if default_handler is None:
		default_handler = h

def unregister_handler(h):
	global default_handler
	handlers.remove(h)
	if default_handler is h:
		try:
			default_handler = handlers[0]
		except IndexError:
			default_handler = None

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

class handler(object):
	"""\
	This abstract class defines the interface used to send and receive
	FS20 datagrams. 
	"""
	def __init__(self,ctx=Context):
		self.last_timestamp = None
		self.ctx = ctx()
	
	def send(self, prefix, data):
		"""\
		Send this datagram.
		"""
		raise NotImplementedError("Dunno how to send datagrams")

	def datagramReceived(self, prefix, data, handler=None, timestamp=None):
		if timestamp is None:
			timestamp = time()
		if self.last_timestamp:
			delta = timestamp - self.last_timestamp
		else:
			delta = None
		self.last_timestamp = timestamp

		if prefix == PREFIX_FS20:
			if len(data) < 4:
				return # obviously way too short

			qs = 0
			for d in data:
				qs += ord(d)
			qs -= ord(data[-1]) # the above loop added it, that's nonsense
			qs = (ord(data[-1]) - qs) & 0xFF # we want the actual difference
	
			code = ord(data[0])*256+ord(data[1])
			try:
				g = groups[(code,qs)]
			except KeyError:
				simple_event(self.ctx, "fs20","unknown",to_hc(code),qs,"".join("%02x" % ord(x) for x in data))
				
			else:
				return g.datagramReceived(data[2:-1], handler, timedelta=delta)
		elif prefix == PREFIX_EM:
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
				simple_event(self.ctx, "fs20","em","checksum1",xs,xsum,"".join("%x" % x for x in data))
				return
			if (qs+5)&15 != qsum:
				simple_event(self.ctx, "fs20","em","checksum2",(qs+5)&15,qsum,"".join("%x" % x for x in data))
				return
			try:
				g = em_procs[data[0]]
				if not g:
					raise IndexError(data[0])
			except IndexError:
				simple_event(self.ctx, "fs20","unknown","em",data[0],"".join("%x"%x for x in data[1:]))
			else:
				r = g(self.ctx, data[1:])
				if r is not None:
					for m,n in r.iteritems():
						simple_event(self.ctx, "fs20","em",g.em_name, (data[1]&7)+1,m,n)
		else:
			simple_event(self.ctx, "fs20","unknown","prefix",prefix,"".join("%02x" % ord(x) for x in data))
			print >>sys.stderr,"Unknown prefix",prefix


class group(object):
	"""\
	This abstract class represents a group of FS20 devices.
	A group is defined by a common house code and checksum offset.
	"""

	handler = None

	def __init__(self, code, qsum):
		self.code = code
		self.qsum = qsum
		code = (code, qsum)
		if code in groups:
			raise RuntimeError("House code %04x already known" % (code,))
		groups[code] = self
	
	def delete(self):
		del groups[(self.code, self.qsum)]

	def datagramReceived(self, data, handler=None):
		raise NotImplementedError("Dunno how to process incoming datagrams")

	def send(self, data, handler=None):
		if handler is None:
			handler = self.handler or default_handler

		data = chr(self.code >> 8) + chr(self.code & 0xFF) + data
		qsum = self.qsum
		for c in data:
			qsum += ord(c)
		data += chr(qsum & 0xFF)

		return handler.send(PREFIX_FS20, data)

