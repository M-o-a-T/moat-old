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

from homevent.module import Module
from homevent.logging import log
from homevent.context import Context
from homevent.parser import parser_builder,parse
from homevent.statement import main_words,Statement,AttributedStatement
from homevent.interpreter import Interpreter
from homevent.base import Name,SName
from homevent.collect import Collection,Collected
from homevent.twist import Jobber
from rpyc import Service
from rpyc.utils.server import ThreadedServer

conn_seq = 0

class RPCconns(Collection):
	name = Name("rpc","connection")
RPCconns = RPCconns()
RPCconns.does("del")

class RPCconn(Service,Collected):
	storage = RPCconns
	dest = ("?unnamed",)
		
	def on_connect(self):
		global conn_seq
		conn_seq += 1
		self.name = self.dest + ("n"+str(conn_seq),)
		Collected.__init__(self)

	def delete(self, ctx=None):
		if self._conn is not None:
			self._conn.close()
		#self.delete_done()
		## called from on_disconnect()

	def on_disconnect(self):
		self.delete_done()

	def exposed_hello(self):
		return "HeLlO!"

	def list(self):
		for r in super(RPCconn,self).list():
			yield r
		import pdb;pdb.set_trace()
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
		self.start_job("job",self.server.start)
		super(RPCserver,self).__init__()

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
	name = "rpc listen"
	doc = "create an RPC server"
	dest = None
	long_doc="""\
Usage: rpc listen ‹name› [‹host›] ‹port›
This command binds a RPyC server to the given port.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) > 3 or len(event)+(self.dest is not None) < 2:
			raise SyntaxError(u'Usage: rpc listen ‹name› [‹host›] ‹port›')
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
	name=("name",)
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
	
	def unload(self):
		main_words.unregister_statement(RPClisten)
	
init = RPCmodule

