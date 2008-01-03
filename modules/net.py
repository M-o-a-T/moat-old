# -*- coding: utf-8 -*-

##
##  Copyright © 2007, Matthias Urlichs <matthias@urlichs.de>
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
This code implements a simple line-oriented protocol via TCP.

"""

from homevent.module import Module
from homevent.logging import log,log_exc,DEBUG,TRACE,INFO,WARN,ERROR
from homevent.statement import Statement, main_words
from homevent.check import Check,register_condition,unregister_condition
from homevent.run import process_failure
from homevent.context import Context
from homevent.event import Event
from homevent.run import process_event,process_failure
from homevent.base import Name
from homevent.collect import Collection,Collected

from twisted.python import failure
from twisted.internet import protocol,reactor,error
from twisted.protocols.basic import LineReceiver,_PauseableMixin

import os

def _call(_,p,*a,**k):
	return p(*a,**k)

class DisconnectedError(RuntimeError):
	def __init__(self,dev):
		self.dev = dev
	def __str__(self):
		return "Disconnected: %s" % (self.dev,)
	
class idErr(RuntimeError):
	def __init__(self,path):
		self.path = path

class TimedOut(idErr):
	def __str__(self):
		return "Timeout: No data at %s" % (self.path,)

class NETerror(EnvironmentError):
	def __init__(self,typ):
		self.typ = typ
	def __str__(self):
		if self.typ < 0:
			try:
				from errno import errorcode
				return "NET_ERR: %d: %s" % (self.typ,errorcode[self.typ])
			except Exception:
				pass
		return "NET_ERR %s" % (self.typ,)

	def __repr__(self):
		return "NETerror(%d)" % (self.typ,)

class NETreceiver(object,LineReceiver, _PauseableMixin):
	"""A receiver for the line protocol.
	"""

	delimiter = "\n"

	def lineReceived(self, line):
		"""Override this.
		"""
		line = line.strip().split()
		process_event(Event(Context(),"net", self.factory.name, *line)).addErrback(process_failure)

	def connectionMade(self):
		super(NETreceiver,self).connectionMade()
		self.factory.haveConnection(self)

	def loseConnection(self):
		if self.transport:
			self.transport.loseConnection()
		if self.factory:
			self.factory.lostConnection(self)
	
	def write(self,val):
		self.transport.write(val+self.delimiter)

class Nets(Collection):
	name = "net"
Nets = Nets()
net_conns = {}


class NETcommon_factory(Collected):
	protocol = NETreceiver
	storage = Nets.storage
	typ = "???"

	def __init__(self, host="localhost", port=4304, name=None, *a,**k):
		if name is None:
			name = "%s:%s" % (host,port)

		self.conn = None
		self.host = host
		self.port = port
		self.name = name
		self.up_event = False
		assert (host,port) not in net_conns, "already known host/port tuple"
		Collected.__init__(self)
		net_conns[(host,port)] = self

	def info(self):
		return "%s %s: %s:%s" % (self.typ, self.name, self.host,self.port)
		
	def list(self):
		yield ("type",self.typ)
		yield ("host",self.host)
		yield ("port",self.port)
		yield ("connected", ("Yes" if self.conn is not None else "No"))

	def haveConnection(self,conn):
		self.drop()
		self.conn = conn

		if not self.up_event:
			self.up_event = True
			process_event(Event(Context(),"net","connect",self.name)).addErrback(process_failure)

	def lostConnection(self,conn):
		if self.conn == conn:
			self.conn = None
			self._down_event()

	def _down_event(self):
		if self.up_event:
			self.up_event = False
			process_event(Event(Context(),"net","disconnect",self.name)).addErrback(process_failure)

	def drop(self):
		"""Kill my connection"""
		if self.conn:
			self.conn.loseConnection()
		
	def write(self,val):
		if self.conn:
			self.conn.write(val)
		else:
			raise DisconnectedError(self.name)

	def end(self):
		c = self.conn
		self.conn = None
		if c:
			c.loseConnection()
			self._down_event()

class NETserver_factory(NETcommon_factory,protocol.ServerFactory):
	typ = "server"
	def end(self):
		try: self._port.stopListening()
		except AttribteError: pass # might be called twice
		del self._port
		super(NETserver_factory,self).end()

class NETclient_factory(NETcommon_factory,protocol.ClientFactory):
	typ = "client"
	def end(self):
		try: self.connector.stopConnecting()
		except error.NotConnectingError: pass
		del self.connector
		super(NETclient_factory,self).end()

	def clientConnectionFailed(self, connector, reason):
		log(WARN,reason)
		self.conn = None
		self._down_event()

	def clientConnectionLost(self, connector, reason):
		log(INFO,reason)
		self.conn = None
		self._down_event()


def connect(host="localhost", port=None, name=None):
	assert port is not None, "Need to provide a port number"
	assert name is not None, "Need to provide a name"
	f = NETclient_factory(host=host, port=port, name=name)
	f.connector = reactor.connectTCP(host, port, f)
	return f

def listen(host="localhost", port=None, name=None):
	assert port is not None, "Need to provide a port number"
	assert name is not None, "Need to provide a name"
	f = NETserver_factory(host=host, port=port, name=name)
	f._port = reactor.listenTCP(port, f, interface=host)
	return f

def disconnect(f):
	assert f==net_conns.pop((f.host,f.port))
	assert f==Nets.pop(f.name)
	f.end()


class NETconnect(Statement):
	name = ("connect","net")
	doc = "connect to a TCP port"
	long_doc="""\
connect net NAME [host] port
- connect (asynchronously) to the TCP server at the remote port;
	name that connection NAME. Default for host is localhost.
	The system will emit a connection-ready event.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 2 or len(event) > 3:
			raise SyntaxError("Usage: connect net ‹name› ‹host›? ‹port›")
		name = event[0]
		if len(event) == 2:
			host = "localhost"
		else:
			host = event[1]
		port = event[-1]

		connect(host,port,name)


class NETlisten(Statement):
	name = ("listen","net")
	doc = "listen to a TCP socket"
	long_doc="""\
listen net NAME [address] port
- listen (asynchronously) on the given port for a TCP connection.
	name that connection NAME. Default for address is loopback.
	The system will emit a connection-ready event when a client
	connects. If another client connects, the old one will be
	disconnected.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 2 or len(event) > 3:
			raise SyntaxError("Usage: connect net ‹name› ‹host›? ‹port›")
		name = event[0]
		if len(event) == 2:
			host = "localhost"
		else:
			host = event[1]
		port = event[-1]

		listen(host,port,name)


class NETsend(Statement):
	name=("send","net")
	doc="send a line to a TCP connection"
	long_doc="""\
send net name text...
	: The text is sent to the named net connection.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		name = Name(event[0])
		val = " ".join(unicode(s) for s in event[1:])
		
		d = Nets[name].write(val)
		return d


class NETdisconnect(Statement):
	name=("disconnect","net")
	doc="disconnect a TCP connection"
	long_doc="""\
disconnect net ‹name›
	: The named net connection is broken.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError("Usage: disconnect net ‹name›")
		name = Name(event[0])
		disconnect(Nets[name])

class NETconnected(Check):
	name=("connected","net")
	doc="Test if a TCP connection is up"
	def check(self,*args):
		if len(args) == 1:
			conn = Nets.get(Name(args[0]),None)
		elif len(args) == 2:
			conn = net_conns.get(Name(args),None)
		else:
			raise SyntaxError(u"Usage: if connected net ‹name›")
		if conn is None:
			return False
		return conn.up_event

class NETexists(Check):
	name=("exists","net")
	doc="Test if a TCP connection is configured"
	def check(self,*args):
		if len(args) == 1:
			return Name(args[0]) in Nets
		elif len(args) == 2:
			return Name(args) in net_conns
		else:
			raise SyntaxError(u"Usage: if exists net ‹name›")

class NETmodule(Module):
	"""\
		Basic TCP connection. Incoming lines are translated to events.
		"""

	info = "Basic line-based TCP access"

	def load(self):
		main_words.register_statement(NETlisten)
		main_words.register_statement(NETconnect)
		main_words.register_statement(NETdisconnect)
		main_words.register_statement(NETsend)
		register_condition(NETexists)
		register_condition(NETconnected)
	
	def unload(self):
		main_words.unregister_statement(NETlisten)
		main_words.unregister_statement(NETconnect)
		main_words.unregister_statement(NETdisconnect)
		main_words.unregister_statement(NETsend)
		unregister_condition(NETexists)
		unregister_condition(NETconnected)
	
init = NETmodule
