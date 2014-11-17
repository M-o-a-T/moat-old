# -*- coding: utf-8 -*-

##
##  Copyright © 2012, Matthias Urlichs <matthias@urlichs.de>
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
This code implements (a subset of) the RRD client protocol.

"""

from __future__ import division,absolute_import

import os
import re

from homevent.module import Module
from homevent.base import Name,SName, singleName
from homevent.logging import log,log_exc,DEBUG,TRACE,INFO,WARN
from homevent.statement import AttributedStatement, Statement, main_words
from homevent.check import Check,register_condition,unregister_condition
from homevent.monitor import Monitor,MonitorHandler, MonitorAgain
from homevent.net import NetConnect,LineReceiver,NetActiveConnector,NetRetry
from homevent.twist import reraise,callLater,fix_exception
from homevent.run import simple_event
from homevent.context import Context
from homevent.times import now,unixtime
from homevent.msg import MsgQueue,MsgFactory,MsgBase, MINE,NOT_MINE, RECV_AGAIN,SEND_AGAIN
from homevent.collect import Collection,Collected

from gevent.event import AsyncResult
from gevent.queue import Full

class RRDchannels(Collection):
	name = "rrd conn"
RRDchannels = RRDchannels()

class RRDservers(Collection):
	name = "rrd server"
RRDservers = RRDservers()
RRDservers.does("del")

class MT_ERROR(singleName): pass # -2 whatever
class MT_ACK(singleName): pass # 0 Oh well
class MT_MULTILINE(MT_ACK): pass # 1 Foo Bar
class MT_OTHER(singleName): pass # ?


class RRDbadResult(RuntimeError):
	pass

class RRDerror(RuntimeError):
	pass

class RRDassembler(LineReceiver):
	buf = None
	lines = 0
	def lineReceived(self, line):
		log("rrd",TRACE,"recv",repr(line))
		msgid = 0
		off = 0
		mt = MT_OTHER

		if self.buf is not None:
			self.buf.append(line)
			self.lines -= 1
			if self.lines == 0:
				buf,self.buf = self.buf,None
				self.msgReceived(type=MT_MULTILINE, msg=buf[0],data=buf[1:])
			return
		elif line == "":
			self.msgReceived(type=MT_OTHER, msg=line)
		elif line[0] == "-":
			off=1
			errno=0
			while off < len(line) and line[off].isdigit():
				errno = 10*errno+int(line[off])
				off += 1
			self.msgReceived(type=MT_ERROR, errno=errno, msg=line[off:].strip())
		elif line[0].isdigit():
			off=0
			lines=0
			while off < len(line) and line[off].isdigit():
				lines = 10*lines+int(line[off])
				off += 1
			if lines:
				self.lines = lines
				self.buf = [line[off:]]
				return
			self.msgReceived(type=MT_ACK, msg=line[off:].strip())
			return
		else:
			self.msgReceived(type=MT_OTHER, msg=line)
	

class RRDchannel(RRDassembler, NetActiveConnector):
	"""A receiver for the protocol used by the rrd adapter."""
	storage = RRDchannels
	typ = "rrd"

	def handshake(self, external=False):
		pass
		# we do not do anything, except to read a prompt

	def down_event(self, external=False):
		simple_event("rrd","disconnect",*self.name)

	def up_event(self, external=False):
		simple_event("rrd","connect",*self.name)

	def not_up_event(self, external=False):
		simple_event("rrd","error",*self.name)


class RRDmsgBase(MsgBase):
	"""a small class to hold the common send() code"""
	def send(self,conn):
		log("rrd",TRACE,"send",repr(self.msg))
		conn.write(self.msg)
		return RECV_AGAIN


class RRDqueue(MsgQueue):
	"""A simple adapter for the RRD protocol."""
	storage = RRDservers
	ondemand = False
	max_send = None

	def __init__(self, name, host,port, *a,**k):
		super(RRDqueue,self).__init__(name=name, factory=MsgFactory(RRDchannel,name=name,host=host,port=port, **k))

	def setup(self):
		self.channel.up_event(False)


class RRDconnect(NetConnect):
	name = "connect rrd"
	dest = None
	doc = "connect to a RRD server"
	port = 42217
	retry_interval = None
	max_retry_interval = None
	timeout_interval = None
	max_timeout_interval = None

	long_doc="""\
connect rrd NAME [[host] port]
- connect to the rrd server at the remote port;
	name that connection NAME. Defaults for host/port are localhost/42217.
	The system will emit connection-ready events.
"""

	def start_up(self):
		q = RRDqueue(name=self.dest, host=self.host,port=self.port)
		if self.retry_interval is not None:
			q.initial_connect_timeout = self.retry_interval
		if self.max_retry_interval is not None:
			q.max_connect_timeout = self.max_retry_interval
		q.start()
		if self.timeout_interval is not None:
			msg = RRDkeepaliveMsg(q, self.timeout_interval,self.max_timeout_interval)
			q.enqueue(msg)
RRDconnect.register_statement(NetRetry)


class RRDconnected(Check):
	name="connected rrd"
	doc="Test if the named rrd server connection is up"
	def check(self,*args):
		assert len(args)==1,"This test requires the connection name"
		try:
			bus = RRDservers[Name(*args)]
		except KeyError:
			return False
		else:
			return bus.channel is not None


# This represents a simple RRD file

class RRDfiles(Collection):
	name = "rrd file"
RRDfiles = RRDfiles()
RRDfiles.does("del")

### simple commands and whatnot

class RRDfile(Collected):
	storage = RRDfiles.storage
	last_sent = None
	last_sent_at = None
	def __init__(self,server,filename,name):
		super(RRDfile,self).__init__(name)
		self.server = server
		self.filename = filename

	def list(self):
		for r in super(RRDfile,self).list():
			yield r
		yield "server",self.server
		yield "filename",self.filename
		if self.last_sent is not None:
			yield ("last_sent",self.last_sent)
			yield ("last_sent_at",self.last_sent_at)



class RRDsetfile(AttributedStatement):
	name="rrd file"
	dest = None
	doc=" a RRD file"

	long_doc = u"""\
rrd file ‹server› ‹path› ‹name…›
  - Send this text (multiple words are space separated) to a controller
rrd file ‹path› ‹name…› :server ‹server›
  - Use this form if you need to use a multi-word server name
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		server = self.dest
		if server is None:
			server = Name(event[0])
			path = event[1]
			name = Name(*event[2:])
		else:
			server = Name(*server.apply(ctx))
			path = event[0]
			name = Name(*event[1:])

		RRDfile(RRDservers[server],path,name)
	
@RRDsetfile.register_statement
class RRDtoserver(Statement):
	name="server"
	doc="specify the (multi-word) name of the server"

	long_doc = u"""\
server ‹name…›
- Use this form for connecting to a server with a multi-word name.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		self.parent.dest = SName(event)


class RRDsendUpdate(RRDmsgBase):
	"""Send a simple command to Wago. Base class."""
	timeout=10
	def __init__(self,file,val):
		super(RRDsendUpdate,self).__init__()
		self.file = file
		self.val = val
		self.file.server.enqueue(self)

	def send(self,conn):
		super(RRDsendUpdate,self).send(conn)
		return RECV_AGAIN

	def recv(self,msg):
		if msg.type is MT_ACK or msg.type is MT_MULTILINE:
			self.result.set(msg.msg)
			return MINE
		if msg.type is MT_ERROR:
			if "illegal attempt to update using time" in msg.msg:
				self.result.set(msg.msg)
			else:
				self.result.set(RRDerror(msg.msg))
			return MINE
		return NOT_MINE

	@property
	def msg(self):
		return "update %s %d:%s" % (self.file.filename,int(unixtime(now())),":".join((str(x) for x in self.val)))


class RRDset(AttributedStatement):
	name="set rrd"
	dest = None
	doc="Send a line to a controller"

	long_doc = u"""\
send rrd ‹val› ‹name…›
  - Set the current value of the named RRD
send rrd ‹val…› :to ‹name…›
  - Set the current values of the named RRD
    Use this if your RRD has more than one non-computed value
	Use "*" as placeholders for values you don't want to set
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		name = self.dest
		if name is None:
			val = (event[0],)
			name = Name(*event[1:])
		else:
			val = list(event)
			name = Name(*name.apply(ctx))

		rrdf = RRDfiles[name]
		rrdf.last_sent = val
		rrdf.last_sent_at = now()
		msg = RRDsendUpdate(rrdf,val)
		res = msg.result.get()
		if isinstance(res,Exception):
			reraise(res)


@RRDset.register_statement
class RRDto(Statement):
	name="to"
	doc="specify the (multi-word) name of the destination RRD"

	long_doc = u"""\
to ‹name…›
- Use this form for RRDs with more than one value.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		self.parent.dest = SName(event)


class RRDmodule(Module):
	"""\
		Talk to a RRD server.
		"""

	info = "Basic RRD server access"

	def load(self):
		main_words.register_statement(RRDconnect)
		main_words.register_statement(RRDsetfile)
		main_words.register_statement(RRDset)
		register_condition(RRDconnected)
		register_condition(RRDchannels.exists)
		register_condition(RRDservers.exists)
		register_condition(RRDfiles.exists)
	
	def unload(self):
		main_words.unregister_statement(RRDconnect)
		main_words.unregister_statement(RRDsetfile)
		main_words.unregister_statement(RRDset)
		unregister_condition(RRDconnected)
		unregister_condition(RRDchannels.exists)
		unregister_condition(RRDservers.exists)
		unregister_condition(RRDfiles.exists)
	
init = RRDmodule
