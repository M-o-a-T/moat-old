# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2015 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
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
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

"""\
This code implements an AMQP connector for MoaT.

"""

import six

from moat import TESTING
from moat.module import Module
from moat.context import Context
from moat.statement import main_words,Statement,AttributedStatement,global_words
from moat.interpreter import Interpreter,ImmediateProcessor
from moat.base import Name,SName
from moat.collect import Collection,Collected,get_collect,all_collect
from moat.check import register_condition,unregister_condition
from moat.twist import Jobber,fix_exception,reraise
from moat.run import process_failure,register_worker,unregister_worker,simple_event
from moat.event import TrySomethingElse
from moat.worker import Worker
from moat.logging import BaseLogger,TRACE,LogNames,LogLevels,DEBUG,log
from moat.times import now

from datetime import datetime,date,time,timedelta
from time import time as itime

import amqp

from gevent.queue import Queue
from gevent.event import AsyncResult
from gevent import spawn,spawn_later

from dabroker.base.codec.json import Codec
json = Codec(None, lists=True)

_seq=0  # new element sequence number
_mseq=0 # new message sequence number
base_mseq="moat.%x."%(int(itime()))

class EventCallback(Worker):
	args = None
	_simple = True

	def __init__(self,conn,parent):
		self.parent = conn
		self.exchange=parent.exchange
		self.strip=parent.strip
		self.prefix = tuple(parent.prefix)
		self._direct = parent.shunt
		self.filter = parent.filter

		if self._direct:
			try: i = self.filter.index('*')
			except ValueError: i = 999
			try: i = min(self.filter.index('*'),i)
			except ValueError: pass
			if i < self.strip or self.strip and not self.filter:
				raise RuntimeError("You can't use 'shunt' if you strip elements you can't restore!")
		for k in self.filter:
			if hasattr(k,'startswith') and k.startswith('*'):
				self._simple = False
				break

		name = parent.dest
		if name is None:
			global _seq
			_seq += 1
			name = SName(conn.name+("f"+str(_seq),))
		self.channel = self.parent.conn.channel()
		self.channel.exchange_declare(exchange=self.exchange, type='topic', auto_delete=False, passive=False)
		super(EventCallback,self).__init__(name)
		register_worker(self, self._direct)
	
	def list(self):
		yield super(EventCallback,self)
		if self.filter:
			yield "filter",self.filter
		if self._direct:
			yield "shunt",True

		yield "parent",self.parent.list()
		yield "exchange",self.exchange
		if self.prefix:
			yield "prefix",self.prefix

	def does_event(self,event):
		if not self.filter:
			return True
		if self._simple:
			return self.filter == event
		ie = iter(event)
		ia = iter(self.filter)
		while True:
			try: e = six.next(ie)
			except StopIteration: e = StopIteration
			try: a = six.next(ia)
			except StopIteration: a = StopIteration
			if e is StopIteration and a is StopIteration:
				return True
			if e is StopIteration or a is StopIteration:
				return False
			if str(a) == '*':
				pass
			elif str(a) == '**':
				return True
			elif str(a) != str(e):
				return False
	
	def process(self, event=None, **k):
		super(EventCallback,self).process(**k)

		# This is an event monitor. Failures will not be tolerated.
		try:
			msg = getattr(event.ctx,'raw',None)
			if msg is None:
				d = {}
				for x,y in event.ctx:
					if x == 'event': continue
					if isinstance(y,six.string_types+six.integer_types+(bool,float,list,tuple)):
						d[x]=y
					elif hasattr(y,'name'):
						d[x]=y.name
				if 'timestamp' not in d:
					d['timestamp'] = now()
				try:
					msg = json.encode(dict(event=list(event), **d))
				except (TypeError,UnicodeDecodeError) as e:
					msg = json.encode(dict(data=repr(event)+"|"+repr(d)+"|"+repr(e)))
			elif isinstance(msg,six.integer_types+(float,)):
				msg = str(msg)
			elif isinstance(msg,six.string_types):
				msg = msg.encode("utf-8")
			global _mseq
			_mseq += 1
			msg = amqp.Message(body=msg, content_type='application/json', message_id=base_mseq+str(_mseq))
			self.channel.basic_publish(msg=msg, exchange=self.exchange, routing_key=".".join(str(x) for x in self.prefix+tuple(event)[self.strip:]))
		except Exception as ex:
			fix_exception(ex)
			process_failure(ex)
			try:
				self.cancel()
			except Exception as ex:
				fix_exception(ex)
				process_failure(ex)
		raise TrySomethingElse

	def cancel(self):
		unregister_worker(self)
		self.parent._stop()
		self.channel.close()
		

class AMQPclients(Collection):
	name = Name("amqp","connection")
AMQPclients = AMQPclients()
#AMQPclients.does("del")

class AMQPclient(Collected,Jobber):
	"""An AMQP link"""
	storage = AMQPclients
	#job = None
	def __init__(self,name,host,port, vhost,username,password):
		self.name = name
		self.host=host
		self.port=port
		self.vhost=vhost
		self.username=username
		self.password=password
		self.workers = []

		try:
			self.conn=amqp.connection.Connection(host=self.host,userid=self.username,password=self.password,login_method='AMQPLAIN', login_response=None, virtual_host=self.vhost)

		except Exception as ex:
			simple_event("amqp","error",*name, error=str(ex), deprecated=True)
			simple_event("amqp","state",*name, error=str(ex), state="error")
			fix_exception(ex)
			process_failure(ex)
		else:
			super(AMQPclient,self).__init__()
			simple_event("amqp","connect",*name, deprecated=True)
			simple_event("amqp","state",*name, state="connect")
			#self.start_job("job",self._loop)

	def _loop(self):
		simple_event("amqp","start",*self.name, _direct=True, deprecated=True)
		simple_event("amqp","state",*self.name, _direct=True, state="up")
		try:
			while True:
				self.conn.drain_events()
		finally:
			simple_event("amqp","stop",*self.name, _direct=True, deprecated=True)
			simple_event("amqp","state",*self.name, _direct=True, state="down")
	
	def _start(self):
		self.start_job('job',self._loop)

	def _stop(self):
		self.stop_job('job')

	def delete(self,ctx=None):
		self.conn.close()
		self.conn = None
		self.stop_job("job")
		simple_event("amqp","disconnect",*self.name, deprecated=True)
		simple_event("amqp","state",*self.name, state="disconnect")
		super(AMQPclient,self).delete()

	def list(self):
		yield super(AMQPclient,self)
		yield ("host",self.host)
		yield ("port",self.port)
		yield ("vhost",self.vhost)
		yield ("user",self.username)
		yield ("password","*"*len(self.password))

class AMQPname(Statement):
	name="name"
	dest = None
	doc="the name of this entry"

	long_doc = u"""\
name ‹name…›
- Name this entry (otherwise it'll be auto-generated)
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		self.parent.dest = SName(event)

class AMQPcname(AMQPname):
	doc="specify the name of the AMQP connection"
	long_doc = u"""\
name ‹name…›
- Use this form for AMQP connections with multi-word names.
"""

class AMQPfilter(Statement):
	name="filter"
	dest = None
	doc="specify the prefix of the events to send"

	long_doc = u"""\
filter ‹name…›
- Use this form for AMQP connection names with multi-word names.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		self.parent.filter = SName(event)

class AMQPexchange(Statement):
	name="exchange"
	dest = None
	doc="specify the exchange to use"

	long_doc = u"""\
exchange ‹name›
- Set the exchange to use.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u'Usage: exchange ‹name›')
		self.parent.exchange = event[0]

class AMQPprefix(Statement):
	name="prefix"
	dest = None
	doc="add a prefix to incoming messages"

	long_doc = u"""\
prefix ‹name…›
- Add ‹name…› in front of incoming messages, for disambiguation.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 1:
			raise SyntaxError(u'Usage: prefix ‹name…›')
		self.parent.prefix = event

class AMQPtopic(Statement):
	name="topic"
	dest = None
	doc="subscripe to this topic"

	long_doc = u"""\
topic ‹filter›
- Only receive messages with this filter; shorten topic
  Format: a.b.c
  * = any one field
  # = zero or more fields
  Default: '#'.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u'Usage: topic ‹filter›')
		self.parent.topic = event[0]

class AMQPstrip(Statement):
	name="strip"
	dest = None
	doc="remove elements from the front of the routing key"

	long_doc = u"""\
strip ‹num›
- Remove the first ‹num› elements from the front of the message's routing key.
  Default: zero.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u'Usage: strip ‹num›')
		self.parent.strip = int(event[0])

class AMQPshunt(Statement):
	name="shunt"
	dest = None
	doc="Send all events out, do not process locally"

	long_doc = u"""\
shunt
- All matching events will be transmitted to this connection.

  They will NOT be processed locally. You NEED an "amqp listen"
  command which receives them from the exchange that's also marked 'shunt'
  and which undoes any processing done here, if you want to not break
  HomEvent.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			raise SyntaxError(u'Usage: shunt')
		self.parent.shunt = True

class AMQPrshunt(AMQPshunt):
	doc="Event tunnel, process locally"

	long_doc = u"""\
shunt
- Use this command to mark the listener as a receiver for a 'shunted'
  "amqp tell" command. You need to make sure to undo any processing
  which that command does.
"""

class AMQPqueue(Statement):
	name="queue"
	dest = None
	doc="specify the queue to use"

	long_doc = u"""\
queue ‹name›
- Set the queue to use.
  Default: moat_event / moat_log.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u'Usage: queue ‹name›')
		self.parent.queue = SName(event)

class AMQPuser(Statement):
	name="user"
	dest = None
	doc="add vhost, username and password"

	long_doc = u"""\
user ‹vhost› ‹username› ‹password›
- Specify virtual host, username, and password for this AMQP connection.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 3:
			raise SyntaxError(u'Usage: user ‹vhost› ‹username› ‹password›')
		self.parent.vhost = event[0]
		self.parent.username = event[1]
		self.parent.password = event[2]

class AMQPconn(AttributedStatement):
	name = "connect amqp"
	doc = "connect to an AMQP server"
	dest = None

	vhost="/"
	username="guest"
	password="guest"
	long_doc="""\
Usage: connect amqp ‹name› ‹host› [‹port›]
This command connects to an AMQP server on the given host/port.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) > 3 or len(event)+(self.dest is not None) < 2:
			raise SyntaxError(u'Usage: connect amqp ‹name› ‹host› [‹port›]')
		if self.dest is None:
			dest = Name(event[0])
			event = event[1:]
		else:
			dest = self.dest
		host = event[0]
		if len(event) > 1:
			port = int(event[1])
		else:
			port = 5672
		AMQPclient(dest,host,port, self.vhost,self.username,self.password)
AMQPconn.register_statement(AMQPuser)
AMQPconn.register_statement(AMQPcname)

class AMQPlogger(BaseLogger):
	"""An AMQP logger"""
	def __init__(self,conn,parent,level=TRACE):
		self.parent=conn
		self.exchange=parent.exchange
		self.prefix=tuple(parent.prefix)
		self.channel = self.parent.conn.channel()
		self.channel.exchange_declare(exchange=self.exchange, type='topic', auto_delete=False, passive=False)
		super(AMQPlogger,self).__init__(level)

	def _log(self, level, *a):
		if LogLevels[level] < self.level:
			return
		try:
			msg = json.encode(dict(level=(LogLevels[level],level),msg=a))
		except TypeError:
			msg = json.encode(dict(level=(LogLevels[level],level),data=repr(a)))

		global _mseq
		_mseq += 1
		msg = amqp.Message(body=msg, content_type='application/json', message_id=base_mseq+str(_mseq))
		self.channel.basic_publish(msg=msg, exchange=self.exchange, routing_key=".".join(str(x) for x in self.prefix+(level,)))
	
	def _flush(self):
		pass

	def delete(self, ctx=None):
		self.parent._stop()
		self.channel.close()
		super(AMQPlogger,self).delete()
		
	def list(self):
		yield super(AMQPlogger,self)
		yield "parent",self.parent
		yield "exchange",self.exchange
		yield "prefix",self.prefix

class AMQPlog(AttributedStatement):
	name = "log amqp"
	doc = "log to an AMQP server"
	dest = None
	exchange = "moat_log"
	prefix=("moat","log")

	long_doc="""\
Usage: log amqp ‹conn› ‹level›
Send logging data to this AMQP exchange.
Defaults: exchange=moat_log level=DEBUG prefix=moat.log
"""
	def run(self,ctx,**k):
		level=DEBUG

		event = self.params(ctx)
		if len(event)+(self.dest is not None) > 2 or len(event)+(self.dest is not None) < 1:
			raise SyntaxError(u'Usage: log amqp ‹conn› [‹level›]')
		if self.dest is None:
			dest = Name(event[0])
			event = event[1:]
		else:
			dest = self.dest
		dest = AMQPclients[dest]
		if len(event) > 0:
			level = LogLevels[event[0]]
		AMQPlogger(dest,self,level)
AMQPlog.register_statement(AMQPname)
AMQPlog.register_statement(AMQPexchange)
AMQPlog.register_statement(AMQPprefix)

class AMQPstart(Statement):
	name = "start amqp"
	doc = "start the AMQP listener"
	prefix = ()

	long_doc="""\
Usage: start amqp ‹conn…›
Start this connection's listener.
Call this method after setting up the channels etc.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 1:
			raise SyntaxError(u'Usage: start amqp ‹conn…›')
		dest = AMQPclients[SName(event)]
		dest._start()

class AMQPstop(Statement):
	name = "stop amqp"
	doc = "stop the AMQP listener"
	prefix = ()

	long_doc="""\
Usage: stop amqp ‹conn…›
Stop this connection's listener.
Call this method before changing the channels etc.

Dangerous! May cause inconsistent state if traffic arrives
at the wrong moment!
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 1:
			raise SyntaxError(u'Usage: stop amqp ‹conn…›')
		dest = AMQPclients[SName(event)]
		dest._stop()

class AMQPtell(AttributedStatement):
	name = "tell amqp"
	doc = "send internal events to an AMQP server"
	dest = None
	prefix = ()
	filter = ()
	strip = 0
	shunt = False

	exchange="moat_event"
	long_doc="""\
Usage: tell amqp ‹conn…›
Send event data to this AMQP exchange.
Default exchange: moat_event
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: tell amqp ‹conn…›')
		dest = AMQPclients[SName(event)]
		worker = EventCallback(dest,self)
AMQPtell.register_statement(AMQPname)
AMQPtell.register_statement(AMQPfilter)
AMQPtell.register_statement(AMQPexchange)
AMQPtell.register_statement(AMQPprefix)
AMQPtell.register_statement(AMQPstrip)
AMQPtell.register_statement(AMQPshunt)

class AMQPrecvs(Collection):
	name = Name("amqp","listener")
AMQPrecvs = AMQPrecvs()
AMQPrecvs.does("del")

class AMQPrecv(Collected):
	"""An AMQP channel receiver"""
	storage = AMQPrecvs
	job = None
	last_recv = None
	def __init__(self, parent,name,conn):
		super(AMQPrecv,self).__init__(name)

		self.chan=conn.conn.channel()
		self.chan.exchange_declare(exchange=parent.exchange, type='topic', auto_delete=False, passive=False)
		res = self.chan.queue_declare(exclusive=True)
		self.chan.queue_bind(exchange=parent.exchange, queue=res.queue, routing_key=parent.topic)
		self.chan.basic_consume(callback=self.on_info_msg, queue=res.queue, no_ack=True)

		self.prefix=tuple(parent.prefix)
		self.strip=parent.strip
		self.exchange=parent.exchange
		self.topic=parent.topic
		self.conn=conn
		self._direct = parent.shunt

	def delete(self, ctx=None):
		self.chan.close()
		super(AMQPrecv,self).delete(ctx=ctx)

	def on_info_msg(self,msg):
		if not self._direct and not TESTING and getattr(msg,'message_id','').startswith(base_mseq):
			return # dup
		if getattr(msg,'content_type','') == "application/json":
			try:
				b = msg.body
				if not isinstance(b,six.text_type):
					b = b.decode('utf-8')
				data = json.decode(b)
				data = json.decode2(data)
			except Exception as e:
				data = { "raw": msg.body, "error": e }
		else:
			data = { "raw": msg.body, "content_type": getattr(msg,'content_type','') }
		self.last_recv = msg.__dict__
		if 'timestamp' not in data:
			data['timestamp'] = now()
		simple_event(*(self.prefix+tuple(msg.routing_key.split('.')[self.strip:])), _direct=self._direct, **data)

	def list(self):
		yield super(AMQPrecv,self)
		if self._direct:
			yield "shunt",True
		yield "connection",self.conn
		yield "exchange",self.exchange
		yield "topic",self.topic
		if self.strip:
			yield "strip",self.strip
		yield "prefix",self.prefix
		if self.last_recv:
			yield "recv", self.last_recv

class AMQPlisten(AttributedStatement):
	name = "listen amqp"
	doc = "read internal events from an AMQP server"
	dest = None
	exchange = "moat_trigger"
	topic = '#'
	prefix = ()
	strip = 0
	shunt = False

	long_doc="""\
Usage: listen amqp ‹conn›
Receive filtered event data from this AMQP exchange.
Default exchange: moat_trigger
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 1:
			raise SyntaxError(u'Usage: listen amqp ‹conn…›')
		conn = AMQPclients[SName(event)]
		dest = self.dest 
		if dest is None:
			global _seq
			_seq += 1
			dest = Name("_amqp","a"+str(_seq))
		AMQPrecv(self, dest,conn)
		
AMQPlisten.register_statement(AMQPname)
AMQPlisten.register_statement(AMQPexchange)
AMQPlisten.register_statement(AMQPprefix)
AMQPlisten.register_statement(AMQPtopic)
AMQPlisten.register_statement(AMQPstrip)
AMQPlisten.register_statement(AMQPrshunt)

class AMQPmodule(Module):
	"""\
		This module implements AMQP access to the MoaT process.
		"""

	info = "AMQP access"

	def load(self):
		main_words.register_statement(AMQPconn)
		main_words.register_statement(AMQPstart)
		main_words.register_statement(AMQPstop)
		main_words.register_statement(AMQPlog)
		main_words.register_statement(AMQPtell)
		main_words.register_statement(AMQPlisten)
		register_condition(AMQPclients.exists)
	
	def unload(self):
		main_words.unregister_statement(AMQPconn)
		main_words.unregister_statement(AMQPstart)
		main_words.unregister_statement(AMQPstop)
		main_words.unregister_statement(AMQPlog)
		main_words.unregister_statement(AMQPtell)
		main_words.unregister_statement(AMQPlisten)
		unregister_condition(AMQPclients.exists)
	
init = AMQPmodule

