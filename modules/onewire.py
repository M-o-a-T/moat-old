# -*- coding: utf-8 -*-

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

"""\
This code implements (a subset of) the OWFS server protocol.

"""

from homevent.module import Module
from homevent.base import Name,SName
from homevent.logging import log,log_exc,DEBUG,TRACE,INFO,WARN
from homevent.statement import Statement, main_words, AttributedStatement
from homevent.check import Check,register_condition,unregister_condition
from homevent.onewire import connect,disconnect, devices
from homevent.net import NetConnect
from homevent.monitor import Monitor,MonitorHandler, MonitorAgain
from homevent.in_out import register_input,register_output, unregister_input,unregister_output, Input,Output

import struct

buses = {}

class OWFSconnect(NetConnect):
	name = "connect onewire"
	doc = "connect to an OWFS server"
	long_doc="""\
connect onewire NAME [[host] port]
	: connect (synchronously) to the onewire server at the remote port;
      name that connection NAME. Defaults for host/port are localhost/4304.
      The system will emit connection-ready and device-present events.
"""

	def start_up(self):
		f = connect(name=self.dest, host=self.host, port=self.port)
		buses[self.dest] = f
		log(TRACE,"New OWFS bus",self.dest,f)


class OWFSdisconnect(Statement):
	name = "disconnect onewire"
	doc = "disconnect from an OWFS server"
	long_doc="""\
disconnect onewire NAME
	: disconnect from the onewire server named NAME.
	  The system will emit connection-closed and device-absent events.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		name = SName(event)
		log(TRACE,"Dropping OWFS bus",name)
		disconnect(buses.pop(name))
		log(TRACE,"Drop OWFS bus",name)


class OWFSio(object):
	typ="onewire"
	def __init__(self, name, params,addons,ranges,values):
		if len(params) != 2:
				raise SyntaxError(u"Usage: %s onewire ‹name…› ‹dev› ‹attr›"%(self.what,))
		self.dev = params[0].lower()
		self.attr = params[1]
		super(OWFSio,self).__init__(name, params,addons,ranges,values)


class OWFSinput(OWFSio,Input):
	what="input"
	doc="An input which reads from 1wire"
	long_doc="""\
onewire dev attr
	: Device ‹dev›'s attribute ‹attr› is read from the bus.
"""
	def _read(self):
		val = devices[self.dev].get(self.attr)
		return val


class OWFSoutput(OWFSio,Output):
	typ="onewire"
	doc="An output which writes to 1wire"
	long_doc="""\
onewire dev attr
	: Device ‹dev›'s attribute ‹attr› is written to the bus.
"""
	def _write(self,val):
		devices[self.dev].set(self.attr, val)


class OWFSset(Statement):
	name="set onewire"
	doc="send a value to a onewire device"
	long_doc=u"""\
set onewire VALUE dev attr
	: ‹VALUE› is written to device ‹dev›'s attribute ‹attr›.
	  This is a one-shot version of ‹output X onewire DEV ATTR› plus ‹set output VALUE X›.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 3:
			raise SyntaxError("Usage: set onewire VALUE DEVICE ATTRIBUTE")
		val, dev, attr = event[:]
		dev = dev.lower()
		
		devices[dev].set(attr, val)


class OWFSdir(AttributedStatement):
	name="dir onewire"
	doc="List a directory on the onewire bus"
	long_doc="""\
dir onewire NAME path...
	List the 1wire devices or attributes on the named bus, at this path.
	(You probably need to quote the device IDs.)
	Alternately, you can list a device's attributes by just passing the
	device ID; the system knows on which bus it is and where.
	For a multi-word bus name, use a separate :name attribute:
		dir onewire "/"
			:name foo bar
"""
	dest=None

	def run(self,ctx,**k):
		event = self.params(ctx)

		def reporter(data):
			print >>ctx.out,data

		if not len(event):
			for d in devices.itervalues():
				print >>ctx.out, (d.typ if hasattr(d,"typ") else "?"), d.id
			print >>ctx.out,"."
		else:
			if len(event) == 1 and event[0].lower() in devices:
				dev = devices[event[0].lower()]
				path = ()
				assert self.dest is None,"Destination only for bus-specific path"
			else:
				if self.dest is None:
					dev = buses[Name(event[0])].root
					path = event[1:]
				else:
					dev = buses[self.dest].root
					path = event
			dev.dir(path=path, proc=reporter)

			print >>ctx.out,"."

class OWFSname(Statement):
	name="name"
	dest = None
	doc="specify the name of the 1wire connection"

	long_doc = u"""\
name ‹name…›
  - Use this form for 1wire connections with multi-word names.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		self.parent.dest = SName(event)

OWFSdir.register_statement(OWFSname)


class OWFSlist(Statement):
	name="list onewire"
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
		elif len(event) == 1 and event[0].lower() in devices:
			dev = devices[event[0].lower()]
			print >>ctx.out,"ID:",dev.bus_id
			print >>ctx.out,"SID:",dev.id
			print >>ctx.out,"Up:", "Yes" \
				if dev.is_up else "Never" if dev.is_up is None else "No"
			if dev.bus: print >>ctx.out,"Bus:",dev.bus.name
			if dev.path: print >>ctx.out,"Path:", "/"+"/".join(dev.path)

		else:
			b = buses[SName(event)]
			print >>ctx.out,"Name:",b.name
			print >>ctx.out,"Host:",b.host
			print >>ctx.out,"Port:",b.port
		print >>ctx.out,"."



class OWFSconnected(Check):
	name="connected onewire"
	doc="Test if a onewire device is accessible"
	def check(self,*args):
		assert len(args),"This test requires the device ID"
		try:
			dev = devices[args[0].lower()]
		except KeyError:
			return False
		else:
			if not dev.is_up: return False
			bus = dev.bus
			if bus is None: return False
			return bus.conn is not None


class OWFSconnectedbus(Check):
	name="connected onewire bus"
	doc="Test if the named onewire server connection is running"
	def check(self,*args):
		assert len(args),"This test requires the connection name"
		try:
			bus = buses[Name(*args)]
		except KeyError:
			return False
		else:
			return bus.conn is not None


class OWFSexists(Check):
	name="exists onewire"
	doc="Test if the onewire device exists"
	def check(self,*args):
		assert len(args)==1,"This test requires the connection name"
		return args[0].lower() in devices

class OWFSexistsbus(Check):
	name="exists onewire bus"
	doc="Test if the named onewire server connection exists"
	def check(self,*args):
		assert len(args)==1,"This test requires the connection name"
		return Name(*args) in buses


class OWFSmon(Monitor):
	queue_len = None # to not use the Watcher queue

	def __init__(self,*a,**k):
		super(OWFSmon,self).__init__(*a,**k)

	def one_value(self, step):
		dev = devices[self.device]
		val = dev.get(self.attribute)
		if self.switch is not None:
			if not self.switched:
				if val > self.high:
					dev.set(self.switch,self.to_high)
					val = dev.get(self.attribute)
					self.switched = True
			else:
				if val < self.low:
					dev.set(self.switch,self.to_low)
					val = dev.get(self.attribute)
					self.switched = False
			if self.switched:
				val += self.high - self.low
		return val

	def up(self):
		dev = devices[self.device]
		if self.switch is not None and self.switched is None:
			log(DEBUG,"switch low1",self.switch,self.to_low)
			dev.set(self.switch,self.to_low)
			self.switched = False
		return super(OWFSmon,self).up()

	def down(self):
		if self.switch is not None:
			self.switched = None
		return super(OWFSmon,self).down()
		

class OWFSwindmon(Monitor):
	def __init__(self,*a,**k):
		super(OWFSwindmon,self).__init__(*a,**k)
		self.avg = None
		self.qavg = None
		self.nval = 0

	def up(self):
		super(OWFSwindmon,self).up()
		self.avg = None
		self.qavg = None
		self.nval = 0

	def list(self):
		for x in super(OWFSwindmon,self).list():
			yield x
		yield ("average",self.avg)
		yield ("turbulence",1-self.qavg)
		yield ("values",self.nval)

	def one_value(self, step):
		dev = devices[self.device]
		val = dev.get(self.attribute)
		val = (float(v.strip()) for v in val.split(","))
		val = (2 if v > 3.5 else 0 if v < 1 else 1 for v in val)
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
		self._process_value(val)
		return self.avg

	def _process_value(self,val):
		if self.avg is None:
			self.avg = val
			self.qavg = 0.5
			decay = self.decay
		else:
			# Principle of operation:
			# Imagine the wind vane traveling on the circumference of
			# a circle (r=1). Calculate a moving average from this
			# point's locations within the circle. Its distance from
			# the center is the accurracy of the current value.
			#
			## c² = a²+b²-2 a b cos α  ⇒
			## α = acos( (a²+b²-c²) / 2 a b )
			from math import pi,cos,acos,sqrt
			def distance(a,b,alpha): return sqrt(a*a+b*b-2*a*b*cos(alpha))
			def angle(a,b,c): return acos((a*a+b*b-c*c)/(2*a*b))

			# Angle between the old average and the new point
			# (center of the circle)
			al = ((self.avg-val)%16)*pi/8

			d = distance(1,self.qavg,al)
			nal = angle(1,d,self.qavg) # at corner of wind vane
			d = (1-self.decay)*d
			self.qavg = distance(1,d,nal)
			nal = angle(1,self.qavg,d) # between avg and new, at center
			if self.avg < val: nal = -nal
			self.avg = (val+nal*8/pi)%16


class OWFSmonitor(MonitorHandler):
	name="monitor onewire"
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
		self.values["device"] = event[0].lower()
		self.values["attribute"] = event[1]
		if "switch" not in self.values:
			self.values["switch"] = None
		self.values["params"] = ("onewire",event[0],event[1])
		if "switch" in self.values and self.values["switch"] is not None:
			self.values["params"] += (u"±"+unicode(self.values["switch"]),)

		super(OWFSmonitor,self).run(ctx,**k)


class MonitorSwitch(Statement):
	name = "switch"
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
	name = "wind"
	doc = "declare a wind instrument"
	long_doc=u"""\
wind ‹offset› ‹weight›
	The monitored device is an AAG wind (direction) meter.
	The attribute you're measuring needs to be "volt.ALL".

	Wind direction is returned as a value in the interval [0,16[
	(N - E - S - W - N).
	The offset specifies where "real" North is in the above list.
	The weight value says how "good" the new value is likely to be; this
	depends somewhat on how turbulent the air usually is around your wind
	vane, and must be between 0 and 1; the defaut is 0.1.

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


class OWFSscan(Statement):
	name="scan onewire"
	doc="(Re-)scan a onewire bus"
	long_doc="""\
scan onewire NAME
	Re-scan this 1wire bus.
	Note that this is done periodically anyway.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)

		if len(event) == 0:
			raise SyntaxError("Usage: scan onewire BUS")
		else:
			try:
				dev = buses[SName(event)]
			except KeyError:
				raise RuntimeError("scan onewire: unknown bus ‹%s›" % (event[0],))
			else:
				return dev.run_watcher()


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
		main_words.register_statement(OWFSscan)
		main_words.register_statement(OWFSset)
		main_words.register_statement(OWFSmonitor)
		register_input(OWFSinput)
		register_output(OWFSoutput)
		register_condition(OWFSconnected)
		register_condition(OWFSexists)
		register_condition(OWFSconnectedbus)
		register_condition(OWFSexistsbus)
	
	def unload(self):
		main_words.unregister_statement(OWFSconnect)
		main_words.unregister_statement(OWFSdisconnect)
		main_words.unregister_statement(OWFSdir)
		main_words.unregister_statement(OWFSlist)
		main_words.unregister_statement(OWFSscan)
		main_words.unregister_statement(OWFSset)
		main_words.unregister_statement(OWFSmonitor)
		unregister_input(OWFSinput)
		unregister_output(OWFSoutput)
		unregister_condition(OWFSconnected)
		unregister_condition(OWFSexists)
		unregister_condition(OWFSconnectedbus)
		unregister_condition(OWFSexistsbus)
	
init = OWFSmodule
