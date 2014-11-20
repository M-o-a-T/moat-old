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
This code implements an AMQP connector for HomEvenT.

"""

from __future__ import division,absolute_import

from homevent import TESTING
from homevent.module import Module
from homevent.context import Context
from homevent.statement import main_words,Statement,AttributedStatement,global_words
from homevent.interpreter import Interpreter,ImmediateProcessor
from homevent.base import Name,SName,flatten
from homevent.collect import Collection,Collected,get_collect,all_collect
from homevent.check import register_condition,unregister_condition
from homevent.twist import Jobber,fix_exception,reraise
from homevent.run import process_failure,register_worker,unregister_worker,simple_event
from homevent.event import TrySomethingElse
from homevent.worker import Worker
from homevent.logging import BaseLogger,TRACE,LogNames,LogLevels,DEBUG,log

from datetime import datetime,date,time,timedelta

import amqp
import json

from gevent.queue import Queue
from gevent.event import AsyncResult
from gevent import spawn,spawn_later

_seq=0

class EventCallback(Worker):
	args = None

	def __init__(self,parent,exchange,prefix,*args):
		self.parent = parent
		self.exchange=exchange
		self.prefix = tuple(prefix)
		if args:
			self.args = SName(args)
			name = SName(parent.name+self.args)
		else:
			name = parent.name
		self.channel = self.parent.conn.channel()
		self.channel.exchange_declare(exchange=self.exchange, type='topic', auto_delete=False, passive=False)
		super(EventCallback,self).__init__(name)
		register_worker(self)
		parent.workers.append(self)
	
	def list(self):
		for r in super(EventCallback,self).list():
			yield r
		if self.args:
			yield "args",self.args
		yield "parent",self.parent.list()
		yield "exchange",self.exchange
		if self.prefix:
			yield "prefix",self.prefix

	def does_event(self,event):
		if self.args is None:
			return True
		ie = iter(event)
		ia = iter(self.args)
		while True:
			try: e = ie.next()
			except StopIteration: e = StopIteration
			try: a = ia.next()
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
			msg=json.dumps(dict(event=list(event)))
			msg = amqp.Message(body=msg, content_type='application/json')
			self.channel.basic_publish(msg=msg, exchange=self.exchange, routing_key=".".join(self.prefix+tuple(event)))
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
		self.parent.drop_worker(self)
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

		except Exception as e:
			simple_event("amqp","error",*name)
		else:
			super(AMQPclient,self).__init__()
			simple_event("amqp","connect",*name)
			#self.start_job("job",self._loop)

	def _loop(self):
		simple_event("amqp","start",*self.name)
		try:
			while True:
				self.conn.drain_events()
		finally:
			simple_event("amqp","stop",*self.name)
	
	def _start(self):
		self.start_job('job',self._loop)

	def _stop(self):
		self.stop_job('job')

	def delete(self,ctx=None):
		self.conn.close()
		self.conn = None
		self.stop_job("job")
		simple_event("amqp","disconnect",*self.name)
		super(AMQPclient,self).delete()

	def list(self):
		for r in super(AMQPclient,self).list():
			yield r
		yield ("host",self.host)
		yield ("port",self.port)
		yield ("vhost",self.vhost)
		yield ("user",self.username)
		yield ("password","*"*len(self.password))

	def drop_worker(self,worker):
		unregister_worker(worker)
		self.workers.remove(worker)

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

class AMQPname(Statement):
	name="name"
	dest = None
	doc="specify the name of the AMQP connection"

	long_doc = u"""\
name ‹name…›
- Use this form for AMQP connection names with multi-word names.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		self.parent.dest = SName(event)
AMQPconn.register_statement(AMQPname)

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
- Only receive messages with this filter
  Format: a.b.c
  * = any one field
  # = zero or more fields
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u'Usage: topic ‹filter›')
		self.parent.topic = event[0]

class AMQPqueue(Statement):
	name="queue"
	dest = None
	doc="specify the queue to use"

	long_doc = u"""\
queue ‹name›
- Set the queue to use.
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
AMQPconn.register_statement(AMQPuser)


class AMQPlogger(BaseLogger):
	"""An AMQP logger"""
	def __init__(self,parent,exchange,kind=None,level=TRACE):
		self.parent=parent
		self.exchange=exchange
		self.kind=kind
		self.channel = self.parent.conn.channel()
		self.channel.exchange_declare(exchange=self.exchange, type='topic', auto_delete=False, passive=False)
		super(AMQPlogger,self).__init__(level)

	def _log(self, level, *a):
		if level < self.level:
			return
		if self.kind is None or a[0] == self.kind:
			msg=json.dumps(dict(level=(level,LogNames[level]),msg=a))
			msg = amqp.Message(body=msg, content_type='application/json')
			self.channel.basic_publish(msg=msg, exchange=self.exchange, routing_key='homevent.log.'+str(a[0])+'.'+LogNames[self.level])
	
	def _flush(self):
		pass

	def delete(self):
		self.channel.close()
		super(AMQPlogger,self).delete()
		
	def list(self):
		for r in super(AMQPlogger,self).list():
			yield r
		yield("parent",self.parent.list())
		yield "exchange",self.exchange

class AMQPlog(AttributedStatement):
	name = "log amqp"
	doc = "log to an AMQP server"
	dest = None
	exchange = "homevent_log"

	long_doc="""\
Usage: log amqp ‹conn› [‹kind› [‹level›]]
Send logging data to this AMQP exchange.
Defaults: exchange=homevent_log kind=* level=DEBUG.
"""
	def run(self,ctx,**k):
		kind=None
		level=DEBUG

		event = self.params(ctx)
		if len(event)+(self.dest is not None) > 3 or len(event)+(self.dest is not None) < 1:
			raise SyntaxError(u'Usage: log amqp ‹conn› [‹kind› [‹level›]]')
		if self.dest is None:
			dest = Name(event[0])
			event = event[1:]
		else:
			dest = self.dest
		dest = AMQPclients[dest]
		if len(event) > 0:
			kind = event[0]
		if len(event) > 1:
			level = LogLevels[event[1]]
		AMQPlogger(dest,self.exchange,kind,level)
AMQPlog.register_statement(AMQPname)
AMQPlog.register_statement(AMQPexchange)

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

	exchange="homevent_event"
	long_doc="""\
Usage: tell amqp ‹conn› ‹arg…›
Send event data to this AMQP exchange.
Default exchange: homevent_event
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event)+(self.dest is not None) < 1:
			raise SyntaxError(u'Usage: tell amqp ‹conn› ‹arg…?›')
		if self.dest is None:
			dest = Name(event[0])
			event = event[1:]
		else:
			dest = self.dest
		dest = AMQPclients[dest]
		worker = EventCallback(dest,self.exchange,self.prefix,*event)
AMQPtell.register_statement(AMQPname)
AMQPtell.register_statement(AMQPexchange)
AMQPtell.register_statement(AMQPprefix)


class AMQPrecvs(Collection):
	name = Name("amqp","listener")
AMQPrecvs = AMQPrecvs()
AMQPrecvs.does("del")

class AMQPrecv(Collected):
	"""An AMQP channel receiver"""
	storage = AMQPrecvs
	job = None
	def __init__(self, parent,name,conn, exchange,topic=None,prefix=()):
		super(AMQPrecv,self).__init__(name)

		topic = topic+".#" if topic else "#"
		self.chan=conn.channel()
		self.chan.exchange_declare(exchange=exchange, type='topic', auto_delete=False, passive=False)
		res = self.chan.queue_declare(exclusive=True)
		self.chan.queue_bind(exchange=exchange, queue=res.queue, routing_key=topic)
		self.chan.basic_consume(callback=self.on_info_msg, queue=res.queue, no_ack=True)

		self.prefix=tuple(prefix)

	def delete(self, ctx=None):
		self.chan.close()
		super(AMQPrecv,self).__delete__(ctx=ctx)

	def on_info_msg(self,msg):
		try:
			data = json.loads(msg.body)
		except Exception:
			data = { "data": msg.body }
		simple_event(*(self.prefix+tuple(msg.routing_key.split('.'))), **data)

class AMQPlisten(AttributedStatement):
	name = "listen amqp"
	doc = "read internal events from an AMQP server"
	dest = None
	exchange = "homevent_trigger"
	topic = None
	prefix = ()

	long_doc="""\
Usage: listen amqp ‹conn›
Receive filtered event data from this AMQP exchange.
Default exchange: homevent_trigger
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
			dest = Name("_amqp",_seq)
		AMQPrecv(self, dest,conn.conn, self.exchange,self.topic,self.prefix)
		
AMQPlisten.register_statement(AMQPname)
AMQPlisten.register_statement(AMQPexchange)
AMQPlisten.register_statement(AMQPprefix)
AMQPlisten.register_statement(AMQPtopic)


class AMQPmodule(Module):
	"""\
		This module implements AMQP access to the HomEvenT process.
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

