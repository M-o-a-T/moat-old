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
This code implements a SSH command line for moat.

"""
import moat
from moat.module import Module
from moat.context import Context
from moat.statement import main_words,Statement,AttributedStatement,global_words
from moat.interpreter import Interpreter,ImmediateProcessor
from moat.base import Name,SName,flatten
from moat.collect import Collection,Collected,get_collect,all_collect
from moat.check import register_condition,unregister_condition
from moat.twist import Jobber,fix_exception,reraise
from moat.run import process_failure,simple_event,register_worker,unregister_worker,MIN_PRIO
from moat.event import TrySomethingElse
from moat.worker import Worker
from moat.logging import BaseLogger,TRACE,LogLevels,LogNames
from moat.times import now

from datetime import datetime,date,time,timedelta
from weakref import ref

from gevent.queue import Queue
from gevent.event import AsyncResult
from gevent import spawn,spawn_later

import qbroker
qbroker.setup(gevent=True)
from qbroker.unit import CC_DICT

conn_seq = 0

class QBconns(Collection):
	name = Name("qbroker","connection")
QBconns = QBconns()
QBconns.does("del")

class RequestTimedOut(RuntimeError):
	pass

class CommandProcessor(ImmediateProcessor):
	"""\
		A processor which runs a command.
		"""

	def simple_statement(self,args):
		fn = self.lookup(args)
		fn.parent = self.parent
		res = fn.run(self.ctx)
		return res

	def complex_statement(self,args):
		fn = self.lookup(args)
		fn.parent = self.parent
		fn.start_block()
		self.fn = fn
		self.fnp = fn.processor
		return self.fnp

	def run(self):
		res = self.fn.run(self.ctx)
		return res

class Reporter(object):
	def __init__(self):
		self.data = []
	def write(self,s):
		self.data.append(s)

def gen_rpcconn(name):
	class namedRPC(QBconn):
		dest = name
	return namedRPC
		

class EventCallback(Worker):
	args = None
	prio = MIN_PRIO+1
	_simple = True

	def __init__(self,parent,*args):
		self.parent = parent
		if args:
			self.args = SName(args)
			for k in self.args:
				if hasattr(k,'startswith') and k.startswith('*'):
					self._simple = False
					break
			name = SName(parent.name+self.args)
			# use self.args because that won't do a multi-roundtrip iteration
		else:
			name = parent.name
		super(EventCallback,self).__init__(name)
	
	def list(self):
		yield super(EventCallback,self)
		if self.args:
			yield("args",self.args)

	def does_event(self,event):
		return True
	
	def process(self, event, queue=None, **k):
		super().process(event=event)

		k.update(event.ctx)
		k['event'] = list(event)
		self.parent.server.alert_gevent('moat.event.'+'.'.join(event), **k)
		raise TrySomethingElse

	def cancel(self):
		self.parent.drop_worker(self)
	exposed_cancel = cancel


class QBconn(Collected,Jobber):
	"""A channel server"""
	storage = QBconns

	def __init__(self,name, host,port,vhost, username,password):
		self.name = name
		self.host=host
		self.port=port
		self.vhost=vhost
		self.username=username
		self.password=password
		super().__init__()
		self.server = qbroker.Unit("moat",amqp=dict(server={'host':self.host,'port':self.port,'virtualhost':self.vhost,'login':self.username,'password':self.password}), loop=qbroker.loop)
		self._rpc_connect()
		self.evt = EventCallback(self)
		register_worker(self.evt)

	def drop_worker(self,w):
		assert w is self.evt
		unregister_worker(self.evt)
		self.evt = None

	def start(self):
		self.server.start_gevent(*getattr(moat,'_args',()))
		simple_event("qbroker","connect",*self.name)

	def delete(self,ctx=None):
		self.server.stop_gevent()
		self.server = None
		super(QBserver,self).delete()
		simple_event("qbroker","disconnect",*self.name)

	def list(self):
		yield super(QBconn,self).list()
		yield ("host",self.host)
		yield ("port",self.port)
		yield ("vhost",self.vhost)
		yield ("server",repr(self.server))
		
	def _rpc_connect(self):
		self.server.register_rpc("moat.list",self._list, call_conv=CC_DICT)
		self.server.register_rpc("moat.cmd",self._command, call_conv=CC_DICT)

	def _command(self, args=(), sub=(),**kwargs):

		ctx = Context(**kwargs)
		ctx.out = Reporter()
		ctx.words = global_words() # self.ctx)

		try:
			if sub:
				cmd = CommandProcessor(parent=self,ctx=ctx)
				proc = cmd.complex_statement(args)
				for s in sub:
					proc.simple_statement(s)
				proc.done()
				cmd.run()
			else:
				CommandProcessor(parent=self,ctx=ctx).simple_statement(args)
		except Exception as e:
			fix_exception(e)
			process_failure(e)
			reraise(e)
		return ctx.out.data

	def _list(self, args=(), **kw):
		c = get_collect(args, allow_collection=True)
		res = []
		if c is None:
			for m in all_collect(skip=False):
				res.append(( m.name,))
		elif isinstance(c,Collection):
			if args[-1] == "*":
				for n,m in c.items():
					res.append(( n,m ))
				return
			for n,m in c.items():
				try:
					m = m.info
				except AttributeError:
					m = m.name
				else:
					if callable(m):
						m = m()
					if isinstance(m,str):
						m = m.split("\n")[0].strip()

				if m is not None:
					res.append(( n,m ))
				else:
					res.append(( n, ))
		else:
			q = Queue(3)
			job = spawn(flatten,q,(c,))
			job.link(lambda _:q.put(None))

			while True:
				r = q.get()
				if r is None:
					break
				p,t = r
				if isinstance(t,datetime):
					if moat.TESTING:
						if t.year != 2003:
							t = "%s" % (humandelta(t-now(t.year != 2003)),)
						else: 
							t = "%s (%s)" % (humandelta(t-now(t.year != 2003)),t)
						ti = t.rfind('.')
						if ti>0 and len(t)-ti > 3 and len(t)-ti<9: # limit to msec
							t= t[:ti+3]+")"
					# otherwise transmit the datetime as-is
				elif not isinstance(t,(date,time,timedelta)):
					t = str(t)

				res.append(( p,t ))
		return res


class QBconnect(AttributedStatement):
	name = "connect qbroker"
	doc = "create an QB server"

	long_doc="""\
Usage: connect qbroker ‹name› [‹host›] ‹port› :vhost ‹name›
This command sets up an AMQP connection to this broker.
"""

	dest = None
	vhost = '/test'
	username="test"
	password="test"

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) > 3 or len(event)+(self.dest is not None) < 2:
			raise SyntaxError(u'Usage: connect qbroker ‹name› [‹host› [‹port›]]')
		if self.dest is None:
			dest = Name(event[0])
			event = event[1:]
		else:
			dest = self.dest
		if len(event) > 1:
			host = event[1]
		else:
			host = "localhost"
		if len(event) > 2:
			port = int(event[2])
		else:
			port = 5672
		q = QBconn(dest,host,port,self.vhost, self.username,self.password)
		try:
			q.start()
		except Exception:
			q.delete()
			raise

class QBname(Statement):
	name="name"
	dest = None
	doc="specify the name of a new TCP connection"

	long_doc = u"""\
name ‹name…›
- Use this form for QB connections with multi-word names.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		self.parent.dest = SName(event)
QBconnect.register_statement(QBname)

class QBvhost(Statement):
	name="vhost"
	dest = None
	doc="specify the virtual host of a QBroker connection"

	long_doc = u"""\
vhost ‹name›
- Change the virtual host to talk to.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError("Usage: vhost ‹name›")
		self.parent.vhost = event[0]
QBconnect.register_statement(QBvhost)

class QBuser(Statement):
	name="user"
	dest = None
	doc="specify the username+password of a QBroker connection"

	long_doc = u"""\
user ‹username› ‹password›
- Set the username and password.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 2:
			raise SyntaxError("Usage: user ‹username› ‹password›")
		self.parent.username = event[0]
		self.parent.password = event[1]
QBconnect.register_statement(QBuser)

class QBmodule(Module):
	"""\
		This module implements QB access to the MoaT process.
		"""

	info = "QB access"

	def load(self):
		main_words.register_statement(QBconnect)
		register_condition(QBconns.exists)
	
	def unload(self):
		main_words.unregister_statement(QBconnect)
		unregister_condition(QBconns.exists)
	
init = QBmodule

