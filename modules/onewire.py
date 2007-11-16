# -*- coding: utf-8 -*-

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
from homevent.monitor import Monitor,MonitorHandler
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
		else:
			b = buses[event[0]]
			print "Name:",b.name
			print "Host:",b.host
			print "Port:",b.port
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

	def one_value(self, step):
		dev = devices[self.device]
		d = dev.get(self.attribute)
		if self.switch is not None:
			log(TRACE,"switch",self.switch)
			def switcher(val):
				if not self.switched:
					if val > self.high:
						log(TRACE,"switch high",self.switch)
						val = dev.set(self.switch,self.to_high)
						val.addCallback(lambda _: dev.get(self.switch))
						val.addCallback(lambda _: _ + self.high - self.low)
						def did_high(_):
							self.switched = True
							return _
						val.addCallback(did_high)
				else:
					if val < self.low:
						log(TRACE,"switch low",self.switch)
						val = dev.set(self.switch,self.to_low)
						val.addCallback(lambda _: dev.get(self.switch))
						def did_low(_):
							self.switched = False
							return _
						val.addCallback(did_low)
					else:
						val += self.high - self.low
				return val
			d.addCallback(switcher)
		else:
			log(TRACE,"no switch")
		return d

	def up(self):
		dev = devices[self.device]
		d = defer.maybeDeferred(super(OWFSmon,self).up)
		if self.switch is not None and self.switched is None:
			d.addCallback(lambda _: dev.set(self.switch,self.to_low))
			def did(_):
				self.switched = False
			d.addCallback(did)
		return d

	def down(self):
		if self.switch is not None:
			self.switched = None
		return super(OWFSmon,self).down()
		

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
