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

		if len(event) < 1:
			raise SyntaxError("Usage: dir onewire BUS [PATH...] / DEV")
		if len(event) == 1 and event[0] in devices:
			dev = devices[event[0]]
			path = ()
		else:
			dev = buses[event[0]].root
			path = event[1:]
		d = dev.dir(path=path, proc=reporter)
		return d


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


class OWFSmodule(Module):
	"""\
		Basic onewire access.
		"""

	info = "Basic one-wire access"

	def load(self):
		main_words.register_statement(OWFSconnect)
		main_words.register_statement(OWFSdisconnect)
		main_words.register_statement(OWFSdir)
		main_words.register_statement(OWFSvar)
		main_words.register_statement(OWFSset)
		register_condition(OWFSconnected)
		register_condition(OWFSexists)
		register_condition(OWFSconnectedbus)
		register_condition(OWFSexistsbus)
	
	def unload(self):
		main_words.unregister_statement(OWFSconnect)
		main_words.unregister_statement(OWFSdisconnect)
		main_words.unregister_statement(OWFSdir)
		main_words.unregister_statement(OWFSvar)
		main_words.unregister_statement(OWFSset)
		unregister_condition(OWFSconnected)
		unregister_condition(OWFSexists)
		unregister_condition(OWFSconnectedbus)
		unregister_condition(OWFSexistsbus)
	
init = OWFSmodule
