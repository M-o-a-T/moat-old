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
This code implements a listener for energy monitoring.

"""

from homevent.module import Module
from homevent.statement import AttributedStatement,Statement, main_words
#from homevent.check import Check,register_condition,unregister_condition
from homevent.run import simple_event
#from homevent.event import Event
#from homevent.context import Context
from homevent.base import Name
from homevent.fs20 import recv_handler, PREFIX
from homevent.collect import Collection,Collected
from homevent.logging import log,TRACE,DEBUG
from homevent.times import now,humandelta
from homevent.timeslot import Timeslots,Timeslotted,Timeslot,collision_filter

#from twisted.internet import protocol,defer,reactor
#from twisted.protocols.basic import _PauseableMixin
#from twisted.python import failure

PREFIX_ENERGY = 'n'

# n030955 17DE000017DE 5F
# Bytenr. Beschreibung
# 1       Type des Sensors 1=EM-1000s 2=EM-100-EM 3=1000GZ
# 2       Die interne Adresse - je nach TYP 1 : 1-4 2: 5-8 3: 9-12
# 3       Fortlaufender Zähler (so kann erkannt werden ob Datenpakete nicht empfangen wurden
# 4-9     Messdaten
# 10      Prüfsumme (Bytes 1-9 mit XOR verknüpft)

# gas
# 4+5     value
# 6+7     zero
# 8+9     value

def en_proc_gas(ctx, data):
	cnt = data[0]*256+data[1]
	return {"counter":cnt}
en_proc_gas.en_name = "gas_meter"
en_proc_gas.interval = 0
en_proc_gas.interval_mod = -0.5

en_procs = [ None,
			 None, # power meter
			 None, # power monitor
             en_proc_gas, # gas meter
           ]

class ens(Collection):
	name = Name("fs20","en")
ens = ens()
ens.does("del")

encodes = {}

class en(Collected,Timeslotted):
	storage = ens.storage
	def __init__(self,name,group,code,ctx, faktor={}, slot=None, delta=None):
		self.ctx = ctx
		self.group = group
		self.code = code
		self.faktor = faktor
		self.last = None # timestamp
		self.delta = delta
		self.last_data = None # data values
		try: g = encodes[group]
		except KeyError: encodes[group] = g = {}
		try: c = g[code]
		except KeyError: g[code] = c = []
		c.append(self)

		self._slot = slot
		if slot is not None:
			ts = Timeslot(self,name)
			p = en_procs[self.group]
			ts.interval = (p.interval + code * p.interval_mod,)
			ts.duration = slot
			ts.maybe_up()
		super(en,self).__init__(*name)

	def get_slot(self):
		if self._slot is None:
			return None
		else:
			return Timeslots[self.name]
	slot = property(get_slot)

	def event(self,ctx,data):
		for m,n in data.iteritems():
			try: n = n * self.faktor[m]
			except KeyError: pass
			else: data[m] = n
			if self.delta is not None:
				if self.last_data:
					val = n-self.last_data[m]
					if val >= 0 or self.delta == 0:
						simple_event(ctx, "fs20","en", m,val, *self.name)
			else:
				simple_event(ctx, "fs20","en", m,n, *self.name)
		self.last = now()
		self.last_data = data

	def info(self):
		if self.last is not None:
			return "%s %d: %s" % (en_procs[self.group].en_name, self.code,
				humandelta(now()-self.last))
		else:
			return "%s %d: (never)" % (en_procs[self.group].en_name, self.code)

	def list(self):
		yield("name",self.name)
		yield("group",self.group)
		yield("groupname",en_procs[self.group].en_name)
		yield("code",self.code)
		if self.last:
			yield ("last",humandelta(now()-self.last))
		if self.last_data:
			for k,v in self.last_data.iteritems(): yield ("last_"+k,v)
		for k,v in self.faktor.iteritems(): yield ("faktor_"+k,v)
		if self.slot:
			for k,v in self.slot.list(): yield ("slot_"+k,v)
	
	def delete(self):
		encodes[self.group][self.code].remove(self)
		if self._slot:
			d = defer.maybeDeferred(self.slot.delete)
		else:
			d = defer.succeed(None)

		def done(_):
			self.delete_done()
			if not encodes[self.group][self.code]: # enpty array
				del encodes[self.group][self.code]
			return _
		d.addBoth(done)
		return d
		

class SomeNull(Exception): pass

def flat(r):
	for a,b in r.iteritems():
		yield a
		yield b

class en_handler(recv_handler):
	def dataReceived(self, ctx, data, handler=None, timedelta=None):
		if len(data) != 10:
			simple_event(ctx, "fs20","en","bad_length","counter",len(data),"".join("%x"%ord(x) for x in data))
			return

		xsum = ord(data[-1])
		data = tuple(ord(d) for d in data[:-1])
		xs=0
		for d in data:
			xs ^= d
		if xs != xsum:
			simple_event(ctx, "fs20","en","checksum",xs,xsum,"".join("%x"%x for x in data))
			return
		try:
			g = en_procs[data[0]]
			if not g:
				raise IndexError(data[0])
		except IndexError:
			simple_event(ctx, "fs20","unknown","en",data[0],"".join("%x"%x for x in data))
		else:
			r = g(ctx, data[3:9])
			if r is None:
				return
			try:
				hdl = encodes[data[0]][data[1]]
			except KeyError:
				simple_event(ctx, "fs20","unknown","en","unregistered",g.en_name,data[1],*tuple(flat(r)))
			else:
				# If there is more than one device on the same
				# address, this code tries to find the one that's
				# most likely to be the one responsible.
				hi = [] # in slot
				hr = [] # slot not running
				hn = [] # device without slot
				for h in hdl:
					if h.slot is None:
						hn.append(h)
					elif h.slot.is_in():
						hi.append(h)
					elif not h.slot.is_out():
						hr.append(h)
				if hi:
					hi = collision_filter(r,hi)
					if len(hi) > 1:
						simple_event(ctx, "fs20","conflict","en","sync",g.en_name,data[1], *tuple(flat(r)))
					else:
						hi[0].slot.do_sync()
						hi[0].event(ctx,r)
				elif hr:
					hr = collision_filter(r,hr)
					if len(hr) > 1:
						simple_event(ctx, "fs20","conflict","en","unsync",g.en_name,data[1], *tuple(flat(r)))
					else:
						hr[0].slot.up(True)
						hr[0].event(ctx,r)
				elif hn:
					hn = collision_filter(r,hn)
					if len(hn) > 1:
						simple_event(ctx, "fs20","conflict","en","untimed",g.en_name,data[1], *tuple(flat(r)))
					else:
						# no timeslot here
						hn[0].event(ctx,r)
				elif hdl:
					simple_event(ctx, "fs20","unknown","en","untimed",g.en_name,data[1], *tuple(flat(r)))
				else:
					simple_event(ctx, "fs20","unknown","en","unregistered",g.en_name,data[1], *tuple(flat(r)))

class en2_handler(en_handler):
	"""Message: m214365"""
	def dataReceived(self, ctx, data, handler=None, timedelta=None):
		if len(data) < 4:
			return
		xd = ""
		db = None
		for d in data:
			d = ord(d)
			xd += chr(d&0x0F) + chr(d>>4)

		super(en2_handler,self).dataReceived(ctx, xd, handler, timedelta)


class FS20en(AttributedStatement):
	name = ("fs20","en")
	doc = "declare an FS20 en monitor"
	long_doc = u"""\
fs20 en ‹name…›:
	code ‹type› ‹id›
	- declare an FS20 environment monitor
Known types: 
"""
	long_doc += "  "+" ".join(n.en_name for n in en_procs if n is not None)+"\n"

	group = None
	code = None
	slot = None
	delta = None
	def __init__(self,*a,**k):
		self.faktor={}
		super(FS20en,self).__init__(*a,**k)

	def run(self,ctx,**k):
		event = self.params(self.ctx)

		if not len(event):
			raise SyntaxError(u"‹fs20 en› needs a name")
		if self.code is None:
			raise SyntaxError(u"‹fs20 en› needs a 'code' sub-statement")
		en(Name(event), self.group,self.code,ctx, self.faktor, self.slot, self.delta)

class FS20enDelta(Statement):
        name = ("delta",)
        doc = "report difference"
        long_doc=u"""\
delta
        Report the difference between the old and new values.
delta up
        Same, but assume that the value only increases.
        Used for counters.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		lo = hi = None
		if len(event) == 0:
			self.parent.delta = 0
		elif len(event) == 1 and event[1] == "up":
			self.parent.delta = 1
		else:
			raise SyntaxError(u'Usage: delta')
FS20en.register_statement(FS20enDelta)


class FS20enScale(Statement):
	name = ("scale",)
	doc = "adapt values"
	long_doc=u"""\
scale ‹type› ‹factor›
	Adjust raw measurements for ‹type› by multiplying by ‹factor›.
	‹type› is the same as reported in the subsequent event.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		lo = hi = None
		if len(event) != 2:
			raise SyntaxError(u'Usage: scale ‹type› ‹factor›')

		name = event[0]
		if event[1] != "*":
			self.parent.factor[name] = float(event[1])
FS20en.register_statement(FS20enScale)

class FS20enSlot(Statement):
	name = ("timeslot",)
	doc = "create a time slot"
	long_doc=u"""\
timeslot [‹seconds›]
	Create a timeslot with the same name as this device.
	Only measurements arriving in that timeslot will be considered.
	You can simply stop the timeslot if you need to re-sync.
	The optional seconds parameter is the duration of the slot;
	it defaults to one second.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) > 1:
			raise SyntaxError(u'Usage: timeslot [‹seconds›]')
		if len(event):
			sec = float(event[0])
		else:
			sec = 1
		self.parent.slot = sec
FS20en.register_statement(FS20enSlot)

class FS20encode(Statement):
	name = ("code",)
	doc = "declare the code type and number for an en device"
	long_doc = u"""\
code ‹type› ‹id›
	- declare the type and ID of an en device
Known types:
"""
	long_doc += "  "+" ".join(n.en_name for n in en_procs if n is not None)+"\n"

	def run(self,ctx,**k):
		event = self.params(self.ctx)
		if len(event) != 2:
			raise SyntaxError(u"Usage: ‹fs20 en› ‹name…›: ‹code› ‹type› ‹id›")
		id = 0
		for p in en_procs:
			if p is not None and p.en_name == event[0]:
				self.parent.group = id
				try:
					id = int(event[1])
				except (TypeError,ValueError):
					raise SyntaxError(u"‹fs20 en› ‹name…›: ‹code›: ID must be a number")
				else:
					if id<0 or id>11:
						raise SyntaxError(u"‹fs20 en› ‹name…›: ‹code›: ID between 0 and 11 please")
					self.parent.code = id
				return
			id += 1
		raise SyntaxError(u"Usage: ‹fs20 en› ‹name…›: ‹code›: Unknown type")
FS20en.register_statement(FS20encode)


class FS20enVal(Statement):
	name = ("set","fs20","en")
	doc = "Set the last-reported value for a device"
	long_doc = u"""\
set fs20 en ‹type› ‹value› ‹name…›
	- Set a last-reported value. This is used to distinguish devices
	  which are set to the same ID after start-up.
"""

	def run(self,ctx,**k):
		event = self.params(self.ctx)
		if len(event) < 3:
			raise SyntaxError(u"Usage: set fs20 en ‹type› ‹value› ‹name…›")
		d = ens[Name(event[2:])]
		if d.last_data is None: d.last_data = {}
		d.last_data[event[0]] = float(event[1])


class fs20en(Module):
	"""\
		Basic fs20 energy monnitor reception.
		"""

	info = "Basic fs20 energy monitor"

	def load(self):
		PREFIX[PREFIX_ENERGY] = en_handler()
		main_words.register_statement(FS20en)
		main_words.register_statement(FS20enVal)
	
	def unload(self):
		del PREFIX[PREFIX_ENERGY]
		main_words.unregister_statement(FS20en)
		main_words.unregister_statement(FS20enVal)
	
init = fs20en
