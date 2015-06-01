# -*- coding: utf-8 -*-
##BP
##
##  Copyright © 2007-2012, Matthias Urlichs <matthias@urlichs.de>
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
from __future__ import division,absolute_import

"""\
This code implements a listener for environment monitoring (tx2/tx3).

"""

from moat.module import Module
from moat.statement import AttributedStatement,Statement, main_words
from moat.run import simple_event
from moat.base import Name,SName
from moat.fs20 import recv_handler, PREFIX
from moat.collect import Collection,Collected
from moat.check import register_condition,unregister_condition
from moat.logging import log,TRACE,DEBUG
from moat.times import now,humandelta
from moat.timeslot import collision_filter

PREFIX_TX = 'x'

def tx_proc_thermo(ctx, data):
	if len(data) != 7:
		simple_event("fs20","tx","bad_length","thermo",len=len(data),data=data)
		return None
	if data[2] != data[5] or data[3] != data[6]:
		simple_event("fs20","tx","bad_repeat","thermo",data=data)
		return None
	temp = data[2]*10 + data[3] + data[4]/10 -50
	return {"temperature":temp}

def tx_proc_hygro(ctx, data):
	if len(data) != 7:
		simple_event("fs20","tx","bad_length","hygro",len=len(data),data=data)
		return None
	if data[2] != data[5] or data[3] != data[6]:
		simple_event("fs20","tx","bad_repeat","hygro",data=data)
		return None
	hum = data[2]*10 + data[3] + data[4]/10
	return {"humidity":hum}


tx_proc_thermo.tx_name = "thermo"
tx_proc_hygro.tx_name = "hygro"

tx_procs = [ tx_proc_thermo,
             None, #1
             None, #2
             None, #3
             None, #4
             None, #5
             None, #6
             None, #7
             None, #8
             None, #9
             None, #A
             None, #B
             None, #C
             None, #D
             tx_proc_hygro, #E
             None, #F
           ]

class TXs(Collection):
	name = Name("fs20","tx")
TXs = TXs()
TXs.does("del")

TXcodes = {}

class TX(Collected):
	storage = TXs.storage
	def __init__(self,name,group,code,ctx, faktor={},offset={}):
		self.ctx = ctx
		self.group = group
		self.code = code
		self.offset = offset
		self.faktor = faktor
		self.last = None # timestamp
		self.last_data = None # data values
		try: g = TXcodes[group]
		except KeyError: TXcodes[group] = g = {}
		try: c = g[code]
		except KeyError: g[code] = c = []
		c.append(self)

		super(TX,self).__init__(*name)

	def event(self,ctx,data):
		d={}
		for m,n in data.items():
			try: n = n * self.faktor[m]
			except KeyError: pass
			try: n = n + self.offset[m]
			except KeyError: pass
			d[m]=n

		simple_event("fs20","tx", *self.name, **d)
		self.last = now()
		self.last_data = data

	def info(self):
		if self.last is not None:
			return "%s %d: %s" % (tx_procs[self.group].tx_name, self.code,
				humandelta(self.last-now()))
		else:
			return "%s %d: (never)" % (tx_procs[self.group].tx_name, self.code)

	def list(self):
		yield("name",self.name)
		yield("group",self.group)
		yield("groupname",tx_procs[self.group].tx_name)
		yield("code",self.code)
		if self.last:
			yield ("last",self.last)
		if self.last_data:
			for k,v in self.last_data.items(): yield ("last_"+k,v)
		for k,v in self.faktor.items(): yield ("faktor_"+k,v)
		for k,v in self.offset.items(): yield ("offset_"+k,v)
	
	def delete(self,ctx=None):
		TXcodes[self.group][self.code].remove(self)
		super(TX,self).delete()
		if not TXcodes[self.group][self.code]: # empty array
			del TXcodes[self.group][self.code]
		

def flat(r):
	for a,b in r.items():
		yield a
		yield b

class tx_handler(recv_handler):
	"""Message: \\x<hex>"""
	def dataReceived(self, ctx, data, handler=None, timedelta=None):
		dat = []
		for d in data:
			d=ord(d)
			dat.append(d>>4)
			dat.append(d&0xF)
		data=dat
		if len(data) < 4:
			return
		if data[0]&1:
			data.pop() # last nibble is missing
		if data[0] != len(data):
			simple_event("fs20","tx","bad_length",len=len(data),data=data)
			return None

		qsum = data[-1]
		qs=0
		for d in data[:-1]:
			qs += d
		if qs&0xF != qsum:
			# fs20¦tx¦checksum¦65¦0¦a0ca791790
			# obviously wrong
			simple_event("fs20","tx","checksum",checksum=qs,checksum_wanted=qsum,data=data)
			#return
		data = data[1:-1]
		try:
			g = tx_procs[data[0]]
			if not g:
				raise IndexError(data[0])
		except IndexError:
			simple_event("fs20","unknown","tx",code=data[0],data=data[1:])
		else:
			r = g(ctx, data[1:])
			if r is None:
				return
			adr = (data[1]<<3) + (data[2]>>1)
			try:
				hdl = TXcodes[data[0]][adr]
			except KeyError:
				simple_event("fs20","unknown","tx","unregistered",type=g.tx_name,adr=adr,**r)
			else:
				# If there is more than one device on the same
				# address, this code tries to find the one that's
				# most likely to be the one responsible.
				hn = collision_filter(r,hdl)
				if len(hn) > 1:
					simple_event("fs20","conflict","tx","untimed",type=g.tx_name,adr=adr, **r)
				elif hn:
					hn[0].event(ctx,r)
				elif hdl:
					simple_event("fs20","unknown","tx","untimed",type=g.tx_name,adr=adr, **r)
				else:
					simple_event("fs20","unknown","tx","unregistered",type=g.tx_name,adr=adr, **r)


class FS20tx(AttributedStatement):
	name = "fs20 tx"
	doc = "declare an FS20 TX2/TX3 monitor"
	long_doc = u"""\
fs20 tx ‹name…›:
	code ‹type› ‹id›
	- declare an FS20 environment monitor (TX2/TX3)
Known types: 
"""
	long_doc += "  "+" ".join(n.tx_name for n in tx_procs if n is not None)+"\n"

	group = None
	code = None
	def __init__(self,*a,**k):
		self.faktor={}
		self.offset={}
		super(FS20tx,self).__init__(*a,**k)

	def run(self,ctx,**k):
		event = self.params(self.ctx)

		if not len(event):
			raise SyntaxError(u"‹fs20 tx› needs a name")
		if self.code is None:
			raise SyntaxError(u"‹fs20 tx› needs a 'code' sub-statement")
		TX(SName(event), self.group,self.code,ctx, self.faktor,self.offset)

class FS20txScale(Statement):
	name = "scale"
	doc = "adapt values"
	long_doc=u"""\
scale ‹type› ‹factor› ‹offset›
	Adjust raw measurements for ‹type› by first multiplying by ‹factor›,
	then adding ‹offset›.
	‹type› is the same as reported in the subsequent event.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		lo = hi = None
		if len(event) != 3:
			raise SyntaxError(u'Usage: scale ‹type› ‹factor› ‹offset›')

		name = event[0]
		if event[1] != "*":
			self.parent.factor[name] = float(event[1])
		if event[2] != "*":
			self.parent.offset[name] = float(event[2])
FS20tx.register_statement(FS20txScale)

class FS20txcode(Statement):
	name = "code"
	doc = "declare the code type and number for a TX device"
	long_doc = u"""\
code ‹type› ‹id›
	- declare the type and ID of a TX device
Known types:
"""
	long_doc += "  "+" ".join(n.tx_name for n in tx_procs if n is not None)+"\n"

	def run(self,ctx,**k):
		event = self.params(self.ctx)
		if len(event) != 2:
			raise SyntaxError(u"Usage: ‹fs20 tx› ‹name…›: ‹code› ‹type› ‹id›")
		id = 0
		for p in tx_procs:
			if p is not None and p.tx_name == event[0]:
				self.parent.group = id
				try:
					id = int(event[1])
				except (TypeError,ValueError):
					raise SyntaxError(u"‹fs20 tx› ‹name…›: ‹code›: ID must be a number")
				else:
					if id<0 or id>127:
						raise SyntaxError(u"‹fs20 tx› ‹name…›: ‹code›: ID between 0 and 127 please")
					self.parent.code = id
				return
			id += 1
		raise SyntaxError(u"Usage: ‹fs20 tx› ‹name…›: ‹code›: Unknown type")
FS20tx.register_statement(FS20txcode)


class FS20txVal(Statement):
	name = "set fs20 tx"
	doc = "Set the last-reported value for a device"
	long_doc = u"""\
set fs20 tx ‹type› ‹value› ‹name…›
	- Set a last-reported value. This is used to distinguish devices
	  which are set to the same ID after start-up.
"""

	def run(self,ctx,**k):
		event = self.params(self.ctx)
		if len(event) < 3:
			raise SyntaxError(u"Usage: set fs20 tx ‹type› ‹value› ‹name…›")
		d = TXs[Name(*event[2:])]
		if d.last_data is None: d.last_data = {}
		d.last_data[event[0]] = float(event[1])


class fs20tx(Module):
	"""\
		Basic fs20 TX2/TX3 reception.
		"""

	info = "Basic fs20 environment monitor for tx2/tx3"

	def load(self):
		PREFIX[PREFIX_TX] = tx_handler()
		main_words.register_statement(FS20tx)
		main_words.register_statement(FS20txVal)
		register_condition(TXs.exists)
	
	def unload(self):
		del PREFIX[PREFIX_TX]
		main_words.unregister_statement(FS20tx)
		main_words.unregister_statement(FS20txVal)
		unregister_condition(TXs.exists)
	
init = fs20tx
