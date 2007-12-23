# -*- coding: utf-8 -*-

##
##  Copyright (C) 2007  Matthias Urlichs <matthias@urlichs.de>
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

"""\
This code implements (a subset of) the OWFS server protocol.

"""

from homevent.module import Module
from homevent.logging import log,log_exc,DEBUG,TRACE,INFO,WARN
from homevent.statement import Statement, main_words
from homevent.check import Check,register_condition,unregister_condition
from homevent.run import process_failure
from twisted.internet import protocol,defer,reactor
from twisted.protocols.basic import _PauseableMixin
from twisted.python import failure
from homevent.onewire import connect,disconnect, devices
from homevent.monitor import Monitor,MonitorHandler, MonitorAgain
import struct


buses = {}

class OWFSconnect(Statement):
	name = ("connect","onewire")
	doc = "connect to an OWFS server"
	long_doc="""\
connect onewire NAME [[host] port]
  - connect (asynchronously) to the onewire server at the remote port;
    name that connection NAME. Defaults for host/port are localhost/4304.
	The system will emit connection-ready and device-present events.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 1 or len(event) > 3:
			raise SyntaxError(u"Usage: connect onewire NAME ‹host?› ‹port›")
		name = event[0]
		k={'name': name}
		if len(event) > 2:
			k['host'] = event[1]
		if len(event) > 1:
			k['port'] = event[-1]

		f = connect(**k)
		buses[name] = f
		log(TRACE,"New OWFS bus",name,f)


class OWFSdisconnect(Statement):
	name = ("disconnect","onewire")
	doc = "disconnect from an OWFS server"
	long_doc="""\
disconnect onewire NAME
  - disconnect (asynchronously) from the onewire server named NAME.
	The system will emit connection-closed and device-absent events.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError("Usage: disconnect onewire NAME")
		name = event[0]
		disconnect(buses.pop(name))
		log(TRACE,"Drop OWFS bus",name)


class OWFSvar(Statement):
	name=("var","onewire")
	doc="assign a variable to get a value off onewire"
	long_doc=u"""\
var onewire NAME dev attr
	: Device ‹dev›'s attribute ‹attr› is read from the bus and stored
	  in the variable ‹NAME›.
	  Note: The value will be fetched when this statement is executed,
	  not when the value is used.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 3:
			raise SyntaxError("Usage: var onewire NAME DEVICE ATTRIBUTE")
		var, dev, attr = event[:]
		
		def got(val):
			setattr(self.parent.ctx,var,val)
		d = devices[dev].get(attr)
		d.addCallback(got)
		return d

class OWFSset(Statement):
	name=("set","onewire")
	doc="send a value to a onewire device"
	long_doc=u"""\
set onewire VALUE dev attr
	: ‹VALUE› is written to device ‹dev›'s attribute ‹attr›.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 3:
			raise SyntaxError("Usage: set onewire VALUE DEVICE ATTRIBUTE")
		val, dev, attr = event[:]
		
		d = devices[dev].set(attr, val)
		return d


class OWFSdir(Statement):
	name=("dir","onewire")
	doc="List a directory on the onewire bus"
	long_doc="""\
dir onewire NAME path...
	List the 1wire devices or attributes on the named bus, at this path.
	(You probably need to quote the device IDs.)
	Alternately, you can list a device's attributes by just passing the
	device ID; the system knows on which bus it is and where.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)

		def reporter(data):
			print >>ctx.out,data

		if not len(event):
			for d in devices.itervalues():
				print >>ctx.out, (d.typ if hasattr(d,"typ") else "?"), d.id
			print >>ctx.out,"."
		else:
			if len(event) == 1 and event[0] in devices:
				dev = devices[event[0]]
				path = ()
			else:
				dev = buses[event[0]].root
				path = event[1:]
			d = dev.dir(path=path, proc=reporter)
			return d


class OWFSlist(Statement):
	name=("list","onewire")
	doc="List known onewire buses"
	long_doc="""\
list onewire [NAME]
	List the 1wire buses.
	If you specify the bus name, additional details will be printed.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)

		if not len(event):
			for b in buses.itervalues():
				print >>ctx.out,b.name
			print >>ctx.out,"."
		elif len(event) != 1:
			raise SyntaxError("Usage: list onewire [BUS]")
		elif event[0] in devices:
			dev = devices[event[0]]
			print >>ctx.out,"ID:",dev.bus_id
			print >>ctx.out,"SID:",dev.id
			print >>ctx.out,"Up:", "Yes" \
				if dev.is_up else "Never" if dev.is_up is None else "No"
			if dev.bus: print >>ctx.out,"Bus:",dev.bus.name
			if dev.path: print >>ctx.out,"Path:", "/"+"/".join(dev.path)

		else:
			b = buses[event[0]]
			print >>ctx.out,"Name:",b.name
			print >>ctx.out,"Host:",b.host
			print >>ctx.out,"Port:",b.port
			print >>ctx.out,"."



class OWFSconnected(Check):
	name=("connected","onewire")
	doc="Test if a onewire device is accessible"
	def check(self,*args):
		assert len(args)==1,"This test requires the device ID"
		try:
			dev = devices[args[0]]
		except KeyError:
			return False
		else:
			if not dev.is_up: return False
			bus = dev.bus
			if bus is None: return False
			return bus.conn is not None


class OWFSconnectedbus(Check):
	name=("connected","onewire","bus")
	doc="Test if the named onewire server connection is running"
	def check(self,*args):
		assert len(args)==1,"This test requires the connection name"
		try:
			bus = buses[args[0]]
		except KeyError:
			return False
		else:
			return bus.conn is not None


class OWFSexists(Check):
	name=("exists","onewire")
	doc="Test if the onewire device exists"
	def check(self,*args):
		assert len(args)==1,"This test requires the connection name"
		return args[0] in devices

class OWFSexistsbus(Check):
	name=("exists","onewire","bus")
	doc="Test if the named onewire server connection exists"
	def check(self,*args):
		assert len(args)==1,"This test requires the connection name"
		return args[0] in buses


class OWFSmon(Monitor):
	def __init__(self,*a,**k):
		super(OWFSmon,self).__init__(*a,**k)

	@defer.inlineCallbacks
	def one_value(self, step):
		dev = devices[self.device]
		val = yield dev.get(self.attribute)
		if self.switch is not None:
			if not self.switched:
				if val > self.high:
					yield dev.set(self.switch,self.to_high)
					val = yield dev.get(self.attribute)
					self.switched = True
			else:
				if val < self.low:
					yield dev.set(self.switch,self.to_low)
					val = yield dev.get(self.attribute)
					self.switched = False
			if self.switched:
				val += self.high - self.low
		defer.returnValue(val)

	@defer.inlineCallbacks
	def up(self):
		dev = devices[self.device]
		if self.switch is not None and self.switched is None:
			log(DEBUG,"switch low1",self.switch,self.to_low)
			yield dev.set(self.switch,self.to_low)
			self.switched = False
		res = yield super(OWFSmon,self).up()
		defer.returnValue(res)

	def down(self):
		if self.switch is not None:
			self.switched = None
		return super(OWFSmon,self).down()
		

class OWFSwindmon(Monitor):
	def __init__(self,*a,**k):
		super(OWFSwindmon,self).__init__(*a,**k)
		self.avg = None
		self.nval = 0

	def up(self):
		super(OWFSwindmon,self).up()
		self.avg = None
		self.nval = 0

	@defer.inlineCallbacks
	def one_value(self, step):
		dev = devices[self.device]
		val = yield dev.get(self.attribute)
		val = (float(v.strip()) for v in val.split(","))
		val = (2 if v > 3 else 0 if v < 1 else 1 for v in val)
		val = tuple(val)
		if   val == (2,2,1,2): val = 0
		elif val == (2,1,1,2): val = 1
		elif val == (2,1,2,2): val = 2
		elif val == (1,1,2,2): val = 3
		elif val == (1,2,2,2): val = 4
		elif val == (1,2,2,0): val = 5
		elif val == (2,2,2,0): val = 6
		elif val == (2,2,0,0): val = 7
		elif val == (2,2,0,2): val = 8
		elif val == (2,0,0,2): val = 9
		elif val == (2,0,2,2): val = 10
		elif val == (0,0,2,2): val = 11
		elif val == (0,2,2,2): val = 12
		elif val == (0,2,2,1): val = 13
		elif val == (2,2,2,1): val = 14
		elif val == (2,2,1,1): val = 15
		else: raise MonitorAgain(val)
		val = (val - self.direction) % 16

		if self.avg is None:
			self.avg = val
		else:
			# The thing is cyclic, thus, when the value crosses zero, we
			# need to make sure that the moving average still makes
			# sense. Otherwise oscillating between 0 and 15 would result
			# in 7.5, which is clearly wrong.
			if abs(val - self.avg) > 8:
				if val > self.avg:
					val -= 16
				else:
					val += 16
			navg = ((1-self.decay)*self.avg + self.decay*val) % 16
			self.avg = navg

		self.nval += 1
		if self.nval < 10*self.decay:
			raise MonitorAgain("decay not reached")

		defer.returnValue(self.avg)


class OWFSmonitor(MonitorHandler):
	name=("monitor","onewire")
	monitor = OWFSmon
	doc="watch a value on the onewire bus"
	long_doc="""\
monitor onewire ‹device› ‹attribute›
	- creates a monitor for a specific value on the bus.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 2:
			raise SyntaxError("Usage: monitor onewire ‹device› ‹attribute›")
		self.values["device"] = event[0]
		self.values["attribute"] = event[1]
		if "switch" not in self.values:
			self.values["switch"] = None
		self.values["params"] = ("onewire",event[0],event[1])
		if "switch" in self.values and self.values["switch"] is not None:
			self.values["params"] += (u"±"+unicode(self.values["switch"]),)

		super(OWFSmonitor,self).run(ctx,**k)


class MonitorSwitch(Statement):
	name = ("switch",)
	doc = "switch between resolutions"
	long_doc=u"""\
switch ‹port› ‹low› ‹high›
	Auto-switch ranges. Initially, set the port to off. When the value
	gets above ‹high›, turn it on and offset the result by ‹high›-‹low›.
	If ‹low› is larger than ‹high›, swap them and turn the port on
	initially.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 3:
			raise SyntaxError(u'Usage: switch ‹port› ‹low› ‹high›')
		val = self.parent.values
		val["switch"] = event[0]
		val["low"] = event[1]
		val["high"] = event[2]
		if val["low"] > val["high"]:
			val["low"] = event[2]
			val["high"] = event[1]
			val["to_low"] = 1
			val["to_high"] = 0
		else:
			val["to_low"] = 0
			val["to_high"] = 1
		val["switched"] = None
MonitorHandler.register_statement(MonitorSwitch)


class MonitorWind(Statement):
	name = ("wind",)
	doc = "declare a wind instrument"
	long_doc=u"""\
wind ‹offset› ‹weight›
	The monitored device is an AAG wind (direction) meter.
	The attribute you're measuring needs to be "volt.ALL".

	Wind direction is a value in the interval [0,16[ (N - E - S - W - N).
	The offset specifies where "real" North is in the above list.
	The weight value says how "good" the new value is likely to be; this
	depends somewhat on how turbulent the air is around your wind vane
	(more tand should be between 0 and 1 (probably closer to zero).


"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) > 2:
			raise SyntaxError(u'Usage: wind ‹offset› ‹weight›')
		val = self.parent.values
		assert self.parent.monitor is OWFSmon, \
			"Wrong monitor (%s)" % (self.parent.monitor,)
		self.parent.monitor = OWFSwindmon

		if len(event) > 0:
			val["direction"] = float(event[0])
			if val["direction"] < 0 or val["direction"] >= 16:
				raise ValueError("weight needs to be between 0 and 15.99")
		else:
			val["direction"] = 0

		if len(event) > 1:
			val["decay"] = float(event[1])
			if val["decay"] < 0 or val["decay"] > 1:
				raise ValueError("weight needs to be between 0 and 1")
		else:
			val["decay"] = 0.1
MonitorHandler.register_statement(MonitorWind)



class OWFSmodule(Module):
	"""\
		Basic onewire access.
		"""

	info = "Basic one-wire access"

	def load(self):
		main_words.register_statement(OWFSconnect)
		main_words.register_statement(OWFSdisconnect)
		main_words.register_statement(OWFSdir)
		main_words.register_statement(OWFSlist)
		main_words.register_statement(OWFSvar)
		main_words.register_statement(OWFSset)
		main_words.register_statement(OWFSmonitor)
		register_condition(OWFSconnected)
		register_condition(OWFSexists)
		register_condition(OWFSconnectedbus)
		register_condition(OWFSexistsbus)
	
	def unload(self):
		main_words.unregister_statement(OWFSconnect)
		main_words.unregister_statement(OWFSdisconnect)
		main_words.unregister_statement(OWFSdir)
		main_words.unregister_statement(OWFSlist)
		main_words.unregister_statement(OWFSvar)
		main_words.unregister_statement(OWFSset)
		main_words.unregister_statement(OWFSmonitor)
		unregister_condition(OWFSconnected)
		unregister_condition(OWFSexists)
		unregister_condition(OWFSconnectedbus)
		unregister_condition(OWFSexistsbus)
	
init = OWFSmodule
