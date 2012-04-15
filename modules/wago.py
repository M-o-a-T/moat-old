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

"""\
This code implements (a subset of) the WAGO server protocol.

"""

from homevent.module import Module
from homevent.base import Name,SName, singleName
from homevent.logging import log,log_exc,DEBUG,TRACE,INFO,WARN
from homevent.statement import AttributedStatement, Statement, main_words
from homevent.check import Check,register_condition,unregister_condition
from homevent.monitor import Monitor,MonitorHandler, MonitorAgain
from homevent.net import NetConnect,LineReceiver,NetActiveConnector
from homevent.msg import MsgQueue,MsgFactory
from homevent.collect import Collection


class WAGOchannel(Collection):
	name = "wago conn"
WAGOchannel = WAGOchannel()

class WAGOserver(Collection):
	name = "wago server"
WAGOserver = WAGOserver()
WAGOserver.does("del")

class MT_MULTILINE(singleName): pass # =foo bar .
class MT_OTHER(singleName): pass # anything else
class MT_INFO(singleName): pass # *
class MT_ERROR(singleName): pass # ?
class MT_ACK(singleName): pass # +
class MT_NAK(singleName): pass # -
class MT_IND(singleName): pass # !num
class MT_IND_ACK(singleName): pass # !+num
class MT_IND_NAK(singleName): pass # !-num

class WAGOassembler(LineReceiver):
	buf = None
	def lineReceived(self, line):
		if self.buf is not None:
			if line == ".":
				msg = self.buf
				self.buf = None
				self.msgReceived(type=MT_MULTILINE, msg=buf)
			else:
				buf.append(line)
		elif line == "":
			self.msgReceived(type=MT_OTHER, msg=line)
		elif line[0] == "=":
			self.buf = [line[1:]]
		elif line[0] == "?":
			self.msgReceived(type=MT_ERROR, msg=line[1:].strip())
		elif line[0] == "*":
			self.msgReceived(type=MT_INFO, msg=line[1:].strip())
		elif line[0] == "+":
			self.msgReceived(type=MT_ACK, msg=line[1:].strip())
		elif line[0] == "-":
			self.msgReceived(type=MT_NAK, msg=line[1:].strip())
		elif line[0] == "!":
			if line[1] == "+":
				mt = MT_IND_ACK
				off = 2
			elif line[1] == "-":
				mt = MT_IND_NAK
				off = 2
			else:
				mt = MT_IND
				off = 1
			msgid = 0
			while off < len(line) and line[off].isdigit():
				msgid = 10*msgid+int(line[off])
				off += 1
			self.msgReceived(type=mt, msgid=msgid, msg=line[off:].strip())
		else:
			self.msgReceived(type=MT_OTHER, msg=line.strip())
	

class WAGOchannel(WAGOassembler, NetActiveConnector):
	"""A receiver for the protocol used by the wago adapter."""
	storage = WAGOchannel
	typ = "wago"


class WAGOqueue(MsgQueue):
	"""A simple adapter for the Wago protocol."""
	storage = WAGOserver
	ondemand = False
	max_send = None

	def __init__(self, name, host,port, *a,**k):
		super(WAGOqueue,self).__init__(name=name, factory=MsgFactory(WAGOchannel,name=name,host=host,port=port, **k))



class WAGOconnect(NetConnect):
	name = ("connect","wago")
	dest = None
	doc = "connect to a Wago server"
	port = 59995
	long_doc="""\
connect wago NAME [[host] port]
- connect to the wago server at the remote port;
	name that connection NAME. Defaults for host/port are localhost/59995.
	The system will emit connection-ready and device-present events.
"""

	def start_up(self):
		q = WAGOqueue(name=self.dest, host=self.host,port=self.port)
		q.start()
		

class WAGOName(Statement):
		name=("name",)
		dest = None
		doc="specify the name of a new Wago connection"

		long_doc = u"""\
name ‹name…›
- Use this form for network connections with multi-word names.
"""

		def run(self,ctx,**k):
				event = self.params(ctx)
				self.parent.dest = SName(event)


class WAGOconnected(Check):
	name="connected wago"
	doc="Test if the named wago server connection is running"
	def check(self,*args):
		assert len(args)==1,"This test requires the connection name"
		try:
			bus = WAGOserver[Name(*args)]
		except KeyError:
			return False
		else:
			return bus.channel is not None

class WAGOexists(Check):
	name="exists wago"
	doc="Test if the named wago server connection exists"
	def check(self,*args):
		assert len(args)>0,"This test requires the connection name"
		return Name(*args) in WAGOserver


class WAGOdisconnect(Statement):
	name = ("disconnect","wago")
	doc = "disconnect from an WAGO server"
	long_doc="""\
disconnect wago NAME
  - disconnect from the wago server named NAME.
	The system will emit connection-closed and device-absent events.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError("Usage: disconnect wago NAME")
		name = event[0]
		log(TRACE,"Dropping WAGO connection",name)
		bus = WAGOserver[name]
		
		log(TRACE,"Drop WAGO connection",name)



class WAGOmon(Monitor):
	queue_len = 1 # use the watcher queue

	def __init__(self,*a,**k):
		pass
		#m = WAGOinput(slot=self.values["slot"], port=self.port)
		#servers[self].add_monitor(self)
		#super(WAGOmon,self).__init__(*a,**k)

	def submit(self,val):
		try:
			self.watcher.put(val,timeout=0)
		except Full:
			simple_event(self.ctx, "monitor","error","overrun",*self.values["params"])
			pass


class WAGOmonitor(MonitorHandler):
	name=("monitor","wago")
	monitor = WAGOmon
	doc="watch a counter on a wago server"
	long_doc="""\
monitor wago ‹device› ‹attribute›
	- creates a monitor for a specific counter on the server.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 3:
			raise SyntaxError("Usage: monitor wago ‹server› ‹slot› ‹port›")
		self.values["slot"] = int(event[-1])
		self.values["port"] = int(event[-2])
		self.values["server"] = event[:-2]
		self.values["params"] = ("wago",)+tuple(event)
		if "switch" in self.values and self.values["switch"] is not None:
			self.values["params"] += (u"±"+unicode(self.values["switch"]),)

		super(WAGOmonitor,self).run(ctx,**k)


class WAGOmodule(Module):
	"""\
		Talk to a Wago server.
		"""

	info = "Basic Wago server access"

	def load(self):
		main_words.register_statement(WAGOconnect)
		main_words.register_statement(WAGOmonitor)
		main_words.register_statement(WAGOdisconnect)
		register_condition(WAGOconnected)
		register_condition(WAGOexists)
	
	def unload(self):
		main_words.unregister_statement(WAGOconnect)
		main_words.unregister_statement(WAGOmonitor)
		main_words.unregister_statement(WAGOdisconnect)
		unregister_condition(WAGOconnected)
		unregister_condition(WAGOexists)
	
init = WAGOmodule
