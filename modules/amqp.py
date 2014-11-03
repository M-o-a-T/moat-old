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

from homevent import TESTING
from homevent.module import Module
from homevent.context import Context
from homevent.parser import parser_builder,parse
from homevent.statement import main_words,Statement,AttributedStatement,global_words
from homevent.interpreter import Interpreter,ImmediateProcessor
from homevent.base import Name,SName,flatten
from homevent.collect import Collection,Collected,get_collect,all_collect
from homevent.check import register_condition,unregister_condition
from homevent.twist import Jobber,fix_exception,reraise
from homevent.run import process_failure,simple_event,register_worker,unregister_worker,MIN_PRIO
from homevent.geventreactor import waitForDeferred
from homevent.event import TrySomethingElse
from homevent.worker import Worker
from homevent.logging import BaseLogger,TRACE,LogNames,LogLevels,DEBUG

from datetime import datetime,date,time,timedelta

import amqp
import json

from gevent.queue import Queue
from gevent.event import AsyncResult
from gevent import spawn,spawn_later

conn_seq = 0

## TODO: inject an event from AMQP

class EventCallback(Worker):
	args = None
	prio = MIN_PRIO+1

	def __init__(self,parent,exchange,*args):
		self.parent = parent
		self.exchange=exchange
		if args:
			self.args = SName(args)
			name = SName(parent.name+self.args)
			# use self.args because that won't do a multi-roundtrip iteration
		else:
			name = parent.name
		self.channel = self.parent.conn.channel()
		self.channel.exchange_declare(exchange=self.exchange, type='fanout', auto_delete=False, passive=False)
		super(EventCallback,self).__init__(name)
		register_worker(self)
		parent.workers.append(self)
	
	def list(self):
		for r in super(EventCallback,self).list():
			yield r
		if self.args:
			yield("args",self.args)
		yield("parent",self.parent.list())
		yield "exchange",self.exchange

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
			self.channel.basic_publish(msg=msg, exchange=self.exchange, routing_key='homevent.event.'+".".join(event))
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
	workers = []
	def __init__(self,name,host,port, vhost,username,password):
		self.name = name
		self.host=host
		self.port=port
		self.vhost=vhost
		self.username=username
		self.password=password

		self.conn=amqp.connection.Connection(host=self.host,userid=self.username,password=self.password,login_method='AMQPLAIN', login_response=None, virtual_host=self.vhost)

		super(AMQPclient,self).__init__()

	def delete(self,ctx=None):
		self.conn.close()
		self.conn = None
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
		self.parent.exchange = SName(event)

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
		self.channel.exchange_declare(exchange=self.exchange, type='fanout', auto_delete=False, passive=False)
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

class AMQPtell(AttributedStatement):
	name = "tell amqp"
	doc = "send internal events to an AMQP server"
	dest = None

	exchange="homevent_event"
	long_doc="""\
Usage: tell amqp ‹conn› ‹arg…›
Send event data to this AMQP exchange.
Default exchange: homevent_event
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event)+(self.dest is not None) < 2:
			raise SyntaxError(u'Usage: tell amqp ‹conn› ‹arg…›')
		if self.dest is None:
			dest = Name(event[0])
			event = event[1:]
		else:
			dest = self.dest
		dest = AMQPclients[dest]
		worker = EventCallback(dest,self.exchange,*event)
AMQPtell.register_statement(AMQPname)
AMQPtell.register_statement(AMQPexchange)

#class AMQPlisten(AttributedStatement):
#	name = "listen amqp"
#	doc = "read internal events from an AMQP server"
#	dest = None
#	filter = "*"
#	queue = "homevent_trigger"
#
#	long_doc="""\
#Usage: listen amqp ‹conn› [‹filter›]
#Send event data to this AMQP exchange.
#Default filter: *
#Default queue name: homevent_trigger
#"""
#	def run(self,ctx,**k):
#		event = self.params(ctx)
#		if len(event)+(self.dest is not None) < 1 or len(event)+(self.dest is not None) > 2:
#			raise SyntaxError(u'Usage: tell amqp ‹conn› ‹arg…›')
#		if self.dest is None:
#			dest = Name(event[0])
#			event = event[1:]
#		else:
#			dest = self.dest
#		dest = AMQPclients[dest]
#		if len(event) > 0:
#			self.filter = event[0]
#		worker = EventInjector(dest,self.filter)
#AMQPlisten.register_statement(AMQPname)
#AMQPlisten.register_statement(AMQPqueue)
#
class AMQPmodule(Module):
	"""\
		This module implements AMQP access to the HomEvenT process.
		"""

	info = "AMQP access"

	def load(self):
		main_words.register_statement(AMQPconn)
		main_words.register_statement(AMQPlog)
		main_words.register_statement(AMQPtell)
		register_condition(AMQPclients.exists)
	
	def unload(self):
		main_words.unregister_statement(AMQPconn)
		main_words.unregister_statement(AMQPlog)
		main_words.unregister_statement(AMQPtell)
		unregister_condition(AMQPclients.exists)
	
init = AMQPmodule

