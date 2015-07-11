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
import six

from moat import TESTING
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
from moat.logging import BaseLogger,TRACE,LogLevels
from moat.times import now

from datetime import datetime,date,time,timedelta
from weakref import ref

from rpyc import Service
from rpyc.core.protocol import DEFAULT_CONFIG
from rpyc.utils.server import ThreadedServer
from rpyc.utils.helpers import async

from gevent.queue import Queue
from gevent.event import AsyncResult
from gevent import spawn,spawn_later

conn_seq = 0

class RPCconns(Collection):
	name = Name("rpc","connection")
RPCconns = RPCconns()
RPCconns.does("del")

class RequestTimedOut(RuntimeError):
	pass

class CallBack(object):
	"""Mix-in to do sane callback handling"""
	callback=None

	def __init__(self,callback=None):
		if callback is None:
			super(CallBack,self).__init__()
			return
		self.callback = async(callback)

	def run_callback(self,*args,**kwargs):
		res = AsyncResult()
		def trigger(res):
			res.set(RequestTimedOut)
		timer = spawn_later(10,trigger,res)
		def done(r):
			res.set(r)
		c = self.callback(*args,**kwargs)
		c.add_callback(done)

		r = res.get()
		if r is not RequestTimedOut:
			timer.kill()

		return r
		
		
	def list(self):
		yield super(CallBack,self)
		yield("callback",repr(self.callback))

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

class EventCallback(Worker,CallBack):
	args = None
	prio = MIN_PRIO+1
	_simple = True

	def __init__(self,parent,callback,*args):
		self.parent = parent
		CallBack.__init__(self,callback)
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
		if self.args is None:
			return True
		if self._simple:
			return self.args == event.name

		ie = iter(event)
		ia = iter(self.args)
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
			elif str(a) != str(e):
				return False
	
	def process(self, **k):
		super(EventCallback,self).process(**k)

		# This is an event monitor. Failures will not be tolerated.
		try:
			self.run_callback(**k)
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
		

class LogCallback(BaseLogger,CallBack):
	def __init__(self,parent,callback,kind=None,level=TRACE):
		self.parent=parent
		self.kind=kind
		CallBack.__init__(self,callback)

		self.name = parent.name
		super(LogCallback,self).__init__(level)

	def _log(self, level, *a):
		if LogLevels.get(level,level) < self.level:
			return
		if TESTING and (a[0].startswith("TEST") or a[-1].endswith("LOGTEST")):
			return
		if self.kind is None or a[0] == self.kind:
			if TESTING:
				a = a+("LOGTEST",)
			self.run_callback(level,*a)
	
	def _flush(self):
		pass

	def cancel(self):
		self.delete()
	exposed_cancel=cancel

class Reporter(object):
	def __init__(self,conn):
		self.conn = ref(conn)
	def write(self,s):
		self.conn().stream.write(s)
class NullReporter(object):
	def write(self,s):
		pass

class RPCconn(Service,Collected):
	storage = RPCconns
	dest = ("?unnamed",)
	workers = None
	doc = "FUBAR"
	stream = NullReporter()
		
	def on_connect(self):
		global conn_seq
		conn_seq += 1
		self.name = self.dest + ("n"+str(conn_seq),)
		self.ctx = Context()
		self.ctx.out = Reporter(self)
		self.ctx.words = global_words(self.ctx)
		self.workers = set()
		simple_event("rpc","connect",*self.name)
		Collected.__init__(self)

	def delete(self, ctx=None):
		if self._conn is not None:
			self._conn.close()
		#super(RPCconn,self).delete()
		## called from on_disconnect()

	def on_disconnect(self):
		simple_event("rpc","disconnect",*self.name)
		if self.workers is not None:
			for w in self.workers:
				unregister_worker(w)
			self.workers = None
		super(RPCconn,self).delete()
	
	def drop_worker(self,worker):
		unregister_worker(worker)
		self.workers.remove(worker)

	def exposed_now(self, force=None):
		return now(force)

	def exposed_cmd_list(self,*args):
		# don't call this 'exposed_list'!
		c = get_collect(args, allow_collection=True)
		try:
			if c is None:
				for m in all_collect(skip=False):
					yield m.name,
			elif isinstance(c,Collection):
				if args[-1] == "*":
					for n,m in c.items():
						yield n,m
					return
				for n,m in c.items():
					try:
						m = m.info
					except AttributeError:
						m = m.name
					else:
						if callable(m):
							m = m()
						if isinstance(m,six.string_types):
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
						t = six.text_type(t)

					yield p,t

		except Exception as e:
				fix_exception(e)
				yield "* ERROR *",repr(e)
				process_failure(e)
				
	def exposed_stdout(self,stream):
		self.stream = stream

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
		return self.ctx[arg]

	def exposed_monitor(self,callback,*args):
		try:
			w = EventCallback(self,callback,*args)
			self.workers.add(w)
			register_worker(w)
			return w
		except Exception as ex:
			fix_exception(ex)
			process_failure(ex)

	def exposed_logger(self,callback,*args):
		l = LogCallback(self,callback,*args)
		return l

	def list(self):
		yield super(RPCconn,self)
		yield ("local host", self._conn._config["endpoints"][0][0])
		yield ("local port", self._conn._config["endpoints"][0][1])
		yield ("remote host", self._conn._config["endpoints"][1][0])
		yield ("remote port", self._conn._config["endpoints"][1][1])
	exposed_list = list

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
		super(RPCserver,self).__init__()
		self.server = ThreadedServer(gen_rpcconn(name), hostname=host,port=port,ipv6=True, protocol_config = {"safe_attrs":set(("list","__str__","__unicode__","year","month","day","days","date","time","hour","minute","second","seconds","microseconds","ctx","items")).union(DEFAULT_CONFIG["safe_attrs"])})
		self.server.listener.settimeout(None)
		self.start_job("job",self._start)

	def _start(self):
		self.server.start()

	def delete(self,ctx=None):
		self.server.close()
		self.server = None
		super(RPCserver,self).delete()

	def list(self):
		yield super(RPCserver,self)
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
		This module implements RPC access to the MoaT process.
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

