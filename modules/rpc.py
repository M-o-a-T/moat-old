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
This code implements a SSH command line for homevent.

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

from datetime import datetime,date,time,timedelta

from rpyc import Service
from rpyc.utils.server import ThreadedServer

from gevent.queue import Queue
from gevent import spawn

conn_seq = 0

class RPCconns(Collection):
	name = Name("rpc","connection")
RPCconns = RPCconns()
RPCconns.does("del")

class CommandProcessor(ImmediateProcessor):
	"""\
		A processor which runs a command.
		"""

	def simple_statement(self,args):
		fn = self.lookup(args)
		fn.parent = self.parent
		res = fn.run(self.ctx)
		res = waitForDeferred(res)
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
		return waitForDeferred(res)


class EventCallback(Worker):
	args = None
	prio = MIN_PRIO+1

	def __init__(self,parent,callback,*args):
		self.parent = parent
		self.callback = callback
		if args:
			self.args = SName(args)
			name = SName(parent.name+self.args)
			# use self.args because that won't do a multi-roundtrip iteration
		else:
			name = parent.name
		super(EventCallback,self).__init__(name)
	
	def list(self):
		for r in super(EventCallback,self).list():
			yield r
		yield("callback",repr(self.callback))
		if self.args:
			yield("args",self.args)

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
			elif str(a) != str(e):
				return False
	
	def process(self, **k):
		super(EventCallback,self).process(**k)

		# This is an event monitor. Failures will not be tolerated.
		try:
			self.callback(**k)
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
	exposed_cancel = cancel
		

class RPCconn(Service,Collected):
	storage = RPCconns
	dest = ("?unnamed",)
	workers = None
		
	def on_connect(self):
		global conn_seq
		conn_seq += 1
		self.name = self.dest + ("n"+str(conn_seq),)
		self.ctx = Context()
		self.ctx.words = global_words(self.ctx)
		self.workers = set()
		simple_event(self.ctx,"rpc","connect",*self.name)
		Collected.__init__(self)

	def delete(self, ctx=None):
		if self._conn is not None:
			self._conn.close()
		#self.delete_done()
		## called from on_disconnect()

	def on_disconnect(self):
		simple_event(self.ctx,"rpc","disconnect",*self.name)
		if self.workers is not None:
			for w in self.workers:
				unregister_worker(w)
			self.workers = None
		self.delete_done()
	
	def drop_worker(self,worker):
		unregister_worker(worker)
		self.workers.remove(worker)

	def exposed_list(self,*args):
		c = get_collect(args, allow_collection=True)
		try:
			if c is None:
				for m in all_collect(skip=False):
					yield m.name,
			elif isinstance(c,Collection):
				for n,m in c.iteritems():
					try:
						m = m.info
					except AttributeError:
						m = m.name
					else:
						if callable(m):
							m = m()
						if isinstance(m,basestring):
							m = m.split("\n")[0].strip()

					if m is not None:
						yield (n,m)
					else:
						yield n,
			else:
				q = Queue(3)
				job = spawn(flatten,q,(c,))
				job.link(lambda _:q.put(None))

				while True:
					res = q.get()
					if res is None:
						return
					p,t = res
					if isinstance(t,datetime):
						if TESTING:
							if t.year != 2003:
								t = "%s" % (humandelta(t-now(t.year != 2003)),)
							else: 
								t = "%s (%s)" % (humandelta(t-now(t.year != 2003)),t)
							ti = t.rfind('.')
							if ti>0 and len(t)-ti > 3 and len(t)-ti<9: # limit to msec
								t= t[:ti+3]+")"
						# otherwise transmit the datetime as-is
					elif not isinstance(t,(date,time,timedelta)):
						t = unicode(t)

					yield p,t

		except Exception as e:
				fix_exception(e)
				yield "* ERROR *",repr(e)
				process_failure(e)
				
	def exposed_command(self,*args,**kwargs):
		try:
			sub = kwargs.get("sub",())
			if sub:
				cmd = CommandProcessor(parent=self,ctx=self.ctx)
				proc = cmd.complex_statement(args)
				for s in sub:
					proc.simple_statement(s)
				proc.done()
				cmd.run()
			else:
				return CommandProcessor(parent=self,ctx=self.ctx).simple_statement(args)
		except Exception as e:
			fix_exception(e)
			process_failure(e)
			reraise(e)

	def exposed_var(self,arg):
		"""Return the value of a variable"""
		return getattr(self.ctx,arg)

	def exposed_monitor(self,callback,*args):
		w = EventCallback(self,callback,*args)
		self.workers.add(w)
		register_worker(w)
		return w

	def list(self):
		for r in super(RPCconn,self).list():
			yield r
		yield ("local host", self._conn._config["endpoints"][0][0])
		yield ("local port", self._conn._config["endpoints"][0][1])
		yield ("remote host", self._conn._config["endpoints"][1][0])
		yield ("remote port", self._conn._config["endpoints"][1][1])

def gen_rpcconn(name):
	class namedRPC(RPCconn):
		dest = name
	return namedRPC
		

class RPCservers(Collection):
	name = Name("rpc","server")
RPCservers = RPCservers()
RPCservers.does("del")

class RPCserver(Collected,Jobber):
	"""A channel server"""
	storage = RPCservers
	def __init__(self,name,host,port):
		self.name = name
		self.host=host
		self.port=port
		self.server = ThreadedServer(gen_rpcconn(name), hostname=host,port=port,ipv6=True)
		self.server.listener.settimeout(None)
		self.start_job("job",self._start)
		super(RPCserver,self).__init__()

	def _start(self):
		self.server.start()

	def delete(self,ctx=None):
		self.server.close()
		self.server = None
		self.delete_done()

	def list(self):
		for r in super(RPCserver,self).list():
			yield r
		yield ("host",self.host)
		yield ("port",self.port)
		yield ("server",repr(self.server))
		

class RPClisten(AttributedStatement):
	name = "listen rpc"
	doc = "create an RPC server"
	dest = None
	long_doc="""\
Usage: listen rpc ‹name› [‹host›] ‹port›
This command binds a RPyC server to the given port.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) > 3 or len(event)+(self.dest is not None) < 2:
			raise SyntaxError(u'Usage: listen rpc ‹name› [‹host›] ‹port›')
		if self.dest is None:
			dest = Name(event[0])
			event = event[1:]
		else:
			dest = self.dest
		port = int(event[-1])
		if len(event) > 1:
			host = event[-2]
		else:
			host = ""
		RPCserver(dest,host,port)

class RPCname(Statement):
	name="name"
	dest = None
	doc="specify the name of a new TCP connection"

	long_doc = u"""\
name ‹name…›
- Use this form for RPC listeners with multi-word names.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		self.parent.dest = SName(event)
RPClisten.register_statement(RPCname)



class RPCmodule(Module):
	"""\
		This module implements RPC access to the HomEvenT process.
		"""

	info = "RPC access"

	def load(self):
		main_words.register_statement(RPClisten)
		register_condition(RPCconns.exists)
		register_condition(RPCservers.exists)
	
	def unload(self):
		main_words.unregister_statement(RPClisten)
		unregister_condition(RPCconns.exists)
		unregister_condition(RPCservers.exists)
	
init = RPCmodule

