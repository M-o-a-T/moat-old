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
This code implements a simple line-oriented protocol via TCP.

"""

from moat.module import Module
from moat.logging import log,DEBUG,TRACE,INFO,WARN,ERROR
from moat.statement import Statement, main_words, AttributedStatement
from moat.check import Check,register_condition,unregister_condition
from moat.base import Name
from moat.collect import Collection,Collected
from moat.run import simple_event
from moat.context import Context

from moat.net import NetListen,NetConnect,NetSend,NetConnected,\
	DisconnectedError,NetListener,NetActiveConnector,NetPassiveConnector,\
	NetName,NetTo,LineReceiver

import os

class Nets(Collection):
	name = "net connection"
Nets = Nets()
Nets.does("del")

netlisten_conns = {}
class NetListens(Collection):
	name = "net server"
NetListens = NetListens()
NetListens.does("del")

net_conns = {}

class NETreceiver(LineReceiver):
	storage = Nets.storage
	storage2 = net_conns

	def lineReceived(self, line):
		line = line.strip().split()
		simple_event("net","recv", *self.name, data=line)

	def down_event(self, external=False):
		simple_event("net","disconnect",*self.name)

	def up_event(self, external=False):
		simple_event("net","connect",*self.name)

	def not_up_event(self, external=False):
		simple_event("net","error",*self.name)

class NETactive(NETreceiver, NetActiveConnector):
	typ = "net_active"
	pass

class NETpassive(NETreceiver, NetPassiveConnector):
	typ = "net_passive"
	pass

class NETlistener(NetListener):
	storage = NetListens.storage

class NETconnect(NetConnect):
	name = "connect net"
	client = NETactive
	doc = "connect to a TCP port"
	long_doc="""\
net NAME [host] port
  - connect (synchronously) to the TCP server at the remote port;
	name that connection NAME. Default for host is localhost.
	The system will emit a connection-ready event.
net [host] port :name NAME…
  - same as above, but allows you to use a multi-word name.
"""
	dest = None

	def error(self,e):
		log(WARN, self.dest, e[1])
		simple_event("net","error",*self.dest)

class NETlisten(NetListen):
	name = "listen net"
	listener = NETlistener
	connector = NETpassive
	doc = "listen to a TCP socket"
	long_doc="""\
listen net NAME [address] port
  - listen (asynchronously) on the given port for a TCP connection.
	name that connection NAME. Default for address is loopback.
	The system will emit a connection-ready event when a client
	connects. If another client connects, the old one will be
	disconnected.
listen net [address] port :to NAME…
  - same as above, but use a multi-word name.

"""
	dest = None

class NETsend(NetSend):
	storage = Nets.storage
	storage2 = net_conns
	name="send net"

class NETconnected(NetConnected):
	storage = Nets.storage
	storage2 = net_conns
	name="connected net"

class NETmodule(Module):
	"""\
		Basic TCP connection. Incoming lines are translated to events.
		"""

	info = "Basic line-based TCP access"

	def load(self):
		main_words.register_statement(NETlisten)
		main_words.register_statement(NETconnect)
		main_words.register_statement(NETsend)
		register_condition(Nets.exists)
		register_condition(NetListens.exists)
		register_condition(NETconnected)
	
	def unload(self):
		main_words.unregister_statement(NETlisten)
		main_words.unregister_statement(NETconnect)
		main_words.unregister_statement(NETsend)
		unregister_condition(Nets.exists)
		unregister_condition(NetListens.exists)
		unregister_condition(NETconnected)
	
init = NETmodule
