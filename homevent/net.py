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
	"""A receiver mix-in for the basic line protocol."""

	delimiter = "\n"
	buffer = ""

	def lineReceived(self, line):
		"""Override this.
		"""
		self.close()
		raise NotImplementedError("You need to override NetReceiver.lineReceived")

	def dataReceived(self,val):
		buffer = self.buffer + val
		data = []

		while True:
			i = buffer.find(self.delimiter)
			if i < 0:
				break
			data.append(buffer[:i])
			buffer = buffer[i+len(self.delimiter):]

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
	job = None
	socket = None

	def __init__(self, name, host,port, socket=None):
		self.socket = socket
		self.host = host
		self.port = port
		self.name = name
		storage2 = getattr(self,"storage2",{})
		assert (host,port) not in storage2, "already known host/port tuple"
		super(NetCommonConnector,self).__init__()
		storage2[(host,port)] = self
		external = (self.socket is not None)
		if self.socket is None:
			try:
				self._connect()
			except Exception as ex:
				fix_exception(ex)
				del storage2[(host,port)]
				self.delete_done()
				try:
					self.not_up_event()
				except Exception as ex2:
					fix_exception(ex2)
					process_failure(ex2)
				reraise(ex)
			self.handshake(False)
		else:
			self.handshake(True)

		def dead(_):
			self.job = None
			if self.socket is not None:
				self.socket.close()
				self.down_event(True)

		self.job = gevent.spawn(self._reader)
		self.job.link(dead)


	def handshake(self, external=False):
		"""Complete the connection, then call .up_event()"""
		self.up_event(external)
		
	def _connect(self):
		e = None
		for res in socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM):
			af, socktype, proto, canonname, sa = res
			try:
				s = socket.socket(af, socktype, proto)
			except socket.error as err:
				fix_exception(err)
				if e is None:
					e = err
				s = None
				continue
			try:
				s.connect(sa)
			except socket.error as err:
				fix_exception(err)
				if e is None:
					e = err
				s.close()
				s = None
				continue
			break
		if s is None:
			reraise(e)
		self.socket = s

	def _reader(self):
		while self.socket is not None:
			try:
				r = self.socket.recv(4096)
				if r is None or r == "":
					return
				self.dataReceived(r)
			except Exception as e:
				fix_exception(e)
				process_failure(e)
	
	def dataReceived(self):
		raise NotImplementedError("You need to override NetCommonConnector.dataReceived()")

	def info(self):
		return "%s %s:%s" % (self.typ, self.host,self.port)
		
	def list(self):
		yield ("type",self.typ)
		yield ("host",self.host)
		yield ("port",self.port)

	def delete(self,ctx=None):
		storage2 = getattr(self,"storage2",None)
		assert storage2 is None or self==storage2.pop((self.host,self.port))
		self.close(external=False)
		self.delete_done()

	def up_event(self,external=False):
		"""Called when a connection has been established"""
		self.close(True)
		raise NotImplementedError("You need to override NetCommonConnector.up_event()")

	def down_event(self,external=True):
		"""Called when an established connection is terminated"""
		raise NotImplementedError("You need to override NetCommonConnector.down_event()")

	def not_up_event(self,external=True):
		"""Called when a connection could not be established in the first place"""
		raise NotImplementedError("You need to override NetCommonConnector.not_up_event()")

	def write(self,val):
		if self.socket:
			self.socket.send(val)
		else:
			raise DisconnectedError(self.name)

	def close(self,external=False):
		r,self.job = self.job,None
		if r:
			r.kill()

		c,self.socket = self.socket,None
		if c:
			c.close()
			self.down_event(external=external)
	def closed(self):
		self.close(external=True)


class NetCommon(AttributedStatement):
	"""Common base class for NetConnect and NetListen commands"""
	#name = ("connect","net")
	#doc = "connect to a TCP port (base class)"
	dest = None
	job = None
	recv = None
	host = "localhost"
	port = None
	long_doc = u"""\
You need to override the long_doc description.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if self.dest is None and len(event):
			self.dest = Name(event[0])
			event = event[1:]
		if (self.host is None and self.port is None and len(event) < 2) or \
		   ((self.host is None or self.port is None) and len(event) == 1) or \
				len(event) > 2:
			raise SyntaxError(u"Usage: %s ‹name› ‹host›%s ‹port›%s" % (" ".join(self.name), "" if self.host is None else "?", "" if self.port is None else "?"))
		if self.port is None:
			if len(event):
				self.port = event[-1]
				event = event[:-1]
			if len(event):
				self.host = event[0]
				event = event[1:]
		else:
			if len(event):
				self.host = event[0]
				event = event[1:]
			if len(event):
				self.port = event[-1]
				event = event[:-1]
		self.start_up()

	def start_up(self):
		raise NotImplementedError("You need to override %s.start_up"%(self.__class__.__name__))

	def error(self,e):
		reraise(e)


##### active connections

class NetActiveConnector(NetCommonConnector):
	"""A connection created by opening a connection via a NetConnect command."""
	typ = "???active"
	pass



class NetConnect(NetCommon):
	#name = ("connect","net")
	doc = "connect to a TCP port (base class)"
	client = NetActiveConnector

	def start_up(self):
		return self.client(name=self.dest, host=self.host,port=self.port)


##### passive connections

name_seq = 0
class NetPassiveConnector(NetCommonConnector):
	"""A connection created by accepting a connection via a NetListener."""
	typ = "???passive"

	def __init__(self,socket,address,name):
		global name_seq
		name_seq += 1

		name = name+(str(name_seq),)
		super(NetPassiveConnector,self).__init__(socket=socket, name=name, host=address[0],port=address[1])


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
		server.start()
	
	def connected(self, socket, address):
		if not self.connector:
			socket.close()
			return
		self.connector(socket,address,self.name)

	def info(self):
		return "%s %s:%s" % (self.typ, self.name,self.connector.name)
		
	def list(self):
		yield ("host", self.host)
		yield ("port", self.port)
		yield ("connector", self.connector.name)

	def delete(self,ctx):
		self.server.stop()
		self.delete_done()


class NetListen(NetCommon):
	#name = ("listen","net")
	doc = "listen to a TCP socket (base class)"

	long_doc = u"""\
You need to override the long_doc description.
"""
	dest = None
	listener = NetListener
	connector = NetPassiveConnector
	default_host = None
	#server = None # descendant of NetServerFactory

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
		event = self.params(ctx)
		name = self.dest
		if name is None:
			name = Name(event[0])
			event = event[1:]
		else:
			name = Name(name.apply(ctx))

		val = u" ".join(unicode(s) for s in event)
		self.storage[name].write(val)

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
			conn = getattr(self,"storage2",{}).get(Name(args),None)
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
		if len(args) == 2 and Name(args) in getattr(self,"storage2",{}):
			return True
		return Name(args) in self.storage

