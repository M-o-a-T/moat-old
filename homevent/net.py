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
This code implements the base for TCP clients and servers.

Your code needs to supply storage and factory class variables.
Look at module/net.py for a basic example.
"""

from homevent.logging import log,log_exc,DEBUG,TRACE,INFO,WARN,ERROR
from homevent.statement import Statement, main_words, AttributedStatement
from homevent.check import Check,register_condition,unregister_condition
from homevent.context import Context
from homevent.event import Event
from homevent.base import Name
from homevent.run import process_failure
from homevent.collect import Collection,Collected
from homevent.twist import fix_exception,reraise

from twisted.internet import protocol,reactor,error
from twisted.protocols.basic import LineReceiver,_PauseableMixin

import os
import sys
import socket

import gevent
from gevent.server import StreamServer

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

class NetError(EnvironmentError):
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
		return "NetError(%d)" % (self.typ,)


class LineReceiver(object):
	"""A receiver for the basic line protocol."""

	delimiter = "\n"
	buffer = ""

	def lineReceived(self, line):
		"""Override this.
		"""
		self.loseConnection()
		raise NotImplementedError("You need to override NetReceiver.lineReceived")

	def dataReceived(self,val):
		buffer = self.buffer + val
		data = []

		i = buffer.index(delimiter)
		while i >= 0:
			data.append(buffer[:i])
			buffer = buffer[i+len(delimiter):]

		self.buffer = buffer
		for d in data:
			try:
				self.lineReceived(d)
			except Exception as e:
				fix_exception(e)
				process_failure(e)
		
	def write(self,val):
		super(LineReceiver,self).write(val+self.delimiter)


#class Nets(Collection):
#	name = "net"
#Nets = Nets()
#Nets.does("del")
#
#net_conns = {}

class NetCommonConnector(Collected):
	"""This class represents one remote network connection."""
	#storage = Nets.storage
	#storage2 = net_conns
	typ = "???common"

	def __init__(self, socket, name, host,port, *a,**k):
		self.socket = socket
		self.host = host
		self.port = port
		self.name = name
		assert (host,port) not in self.storage2, "already known host/port tuple"
		super(NetCommonConnector,self).__init__()
		self.storage2[(host,port)] = self

		def dead(_):
			self.job = None
			if self.socket is not None:
				self.socket.close()
				self.down_event()

		self.job = gevent.spawn(self._reader)
		self.job.link(dead)

		try:
			self.up_event()
		except Exception:
			self.end()
			raise

	def _reader(self):
		while True:
			r = self.socket.recv(4096)
			if r is None:
				return
			self.dataReceived(r)
	
	def dataReceived(self):
		raise NotImplementedError("You need to override NetCommonConnector.dataReceived()")

	def info(self):
		return "%s %s:%s" % (self.typ, self.host,self.port)
		
	def list(self):
		yield ("type",self.typ)
		yield ("host",self.host)
		yield ("port",self.port)

	def delete(self,ctx):
		assert self==self.storage2.pop((self.host,self.port))
		self.end()
		self.delete_done()

	def up_event(self):
		self.end()
		raise NotImplementedError("You need to override NetCommonConnector.up_event()")

	def down_event(self):
		raise NotImplementedError("You need to override NetCommonConnector.down_event()")

	def write(self,val):
		if self.socket:
			self.socket.write(val)
		else:
			raise DisconnectedError(self.name)

	def end(self):
		r,self.job = self.job,None
		if r:
			r.kill()

		c,self.socket = self.socket,None
		if c:
			c.close()
			self.down_event()


##### active connections

class NetActiveConnector(NetCommonConnector):
	"""A connection created by opening a connection via a NetConnect command."""
	typ = "???active"
	pass


class NetConnect(AttributedStatement):
	#name = ("net",)
	doc = "connect to a TCP port (base class)"
	dest = None
	job = None
	recv = None
	client = NetActiveConnector
	long_doc = u"""\
You need to override the long_doc description.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 1+(self.dest is None) or len(event) > 2+(self.dest is None):
			raise SyntaxError(u"Usage: net ‹name› ‹host›? ‹port›")
		name = self.dest
		if name is None:
			self.dest = Name(event[0])
			event = event[1:]
		if len(event) == 1:
			self.host = "localhost"
		else:
			self.host = event[0]
		self.port = event[-1]
		self.start_up()

	def start_up(self):
		s = None
		e = None
		for res in socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM):
			af, socktype, proto, canonname, sa = res
			try:
				s = socket.socket(af, socktype, proto)
			except socket.error:
				if e is None:
					e = sys.exc_info()
				s = None
				continue
			try:
				s.connect(sa)
			except socket.error:
				if e is None:
					e = sys.exc_info()
				s.close()
				s = None
				continue
			break
		if s is None:
			self.error(e)
			return
		self.client(s,name=self.dest, host=self.host,port=self.port)

	def error(self,e):
		reraise(e)


##### passive connections

name_seq = 0
class NetPassiveConnector(NetCommonConnector):
	"""A connection created by accepting a connection via a NetListener."""
	typ = "???passive"

	def __init__(self,socket,address,name):
		global name_seq
		name_seq += 1

		name = name+("N"+str(name_seq),)
		super(NetPassiveConnector,self).__init__(socket, name=name, host=address[0],port=address[1])


class NetListener(Collected):
	"""Something which accepts connections to a specific address/port."""
	#storage = Nets.storage
	server = None
	connector = None

	def __init__(self, name, host,port, *a,**k):
		super(NetListener,self).__init__(name)
		self.name = name
		self.host = host
		self.port = port

	def _init2(self, server, connector):
		"""The server and this object are cross-connected, so this step finishes initialization."""
		self.server = server
		self.connector = connector
	
	def connected(self, socket, address):
		if not self.connector:
			socket.close()
			return
		self.connector(socket,address)

	def info(self):
		return "%s %s:%s" % (self.typ, self.name,self.connector.name)
		
	def list(self):
		yield ("host", self.host)
		yield ("port", self.port)
		yield ("connector", self.connector.name)

	def delete(self,ctx):
		self.server.stop()
		self.delete_done()


class NetListen(AttributedStatement):
	#name = ("listen","net")
	doc = "listen to a TCP socket (base class)"

	long_doc = u"""\
You need to override the long_doc description.
"""
	dest = None
	listener = NetListener
	connector = NetPassiveConnector
	#server = None # descendant of NetServerFactory

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 1+(self.dest is None) or len(event) > 2+(self.dest is None):
			raise SyntaxError(u"Usage: listen net ‹name› ‹host›? ‹port›")
		name = self.dest
		if name is None:
			self.dest = Name(event[0])
			event = event[1:]
		if len(event) == 2:
			self.host = "localhost"
		else:
			self.host = event[1]
		self.port = event[-1]
		self.start_up()

	def start_up(self):
		r = self.listener(name=self.dest, host=self.host,port=self.port)
		s = StreamServer((self.host, self.port), r.connected)
		r._init2(s, self.connector)


class NetName(Statement):
	name=("name",)
	dest = None
	doc="specify the name of a new TCP connection"

	long_doc = u"""\
name ‹name…›
  - Use this form for network connections with multi-word names.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		self.parent.dest = Name(event)
NetConnect.register_statement(NetName)
NetListen.register_statement(NetName)


class NetSend(AttributedStatement):
	#storage = Nets.storage
	#storage2 = net_conns
	#name=("send","net")
	dest = None
	doc="send a line to a TCP connection"
	long_doc=u"""\
send net ‹name› text…
  - The text is sent to the named net connection.
send net text… :to ‹name…›
  - as above, but works with a multi-word connection name.

"""
	def run(self,ctx,**k):
		import pdb;pdb.set_trace()
		event = self.params(ctx)
		name = self.dest
		if name is None:
			name = Name(event[0])
			event = event[1:]
		else:
			name = Name(name.apply(ctx))

		val = u" ".join(unicode(s) for s in event)
		d = self.storage[name].write(val)
		return d

class NetTo(Statement):
	name=("to",)
	dest = None
	doc="specify which TCP connection to use"

	long_doc = u"""\
to ‹name…›
  - Use this form for network connections with multi-word names.
"""

	def run(self,ctx,**k):
		self.parent.dest = self.par(ctx)
NetSend.register_statement(NetTo)


class NetConnected(Check):
	#storage = Nets.storage
	#storage2 = net_conns
	name=("connected","net")
	doc="Test if a TCP connection is up"

	def check(self,*args):
		conn = None
		if len(args) == 2:
			conn = self.storage2.get(Name(args),None)
		if conn is None:
			conn = self.storage.get(Name(args))
		if conn is None:
			return False
		return conn.did_up_event

class NetExists(Check):
	#storage = Nets.storage
	#storage2 = net_conns
	#name=("exists","net")
	doc="Test if a TCP connection is configured"

	def check(self,*args):
		if len(args) == 2 and Name(args) in self.storage2:
			return True
		return Name(args) in self.storage

