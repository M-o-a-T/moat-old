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
This code implements a simple line-oriented protocol via TCP.

"""

from homevent.module import Module
from homevent.logging import log,log_exc,DEBUG,TRACE,INFO,WARN,ERROR
from homevent.statement import Statement, main_words, AttributedStatement
from homevent.check import Check,register_condition,unregister_condition
from homevent.base import Name
from homevent.collect import Collection,Collected
from homevent.run import simple_event
from homevent.context import Context

from twisted.internet import protocol,reactor,error

from homevent.net import NetListen,NetConnect,NetSend,NetExists,NetConnected,\
	DisconnectedError,NetListener,NetActiveConnector,NetPassiveConnector,\
	NetName,NetTo,LineReceiver

import os

class Nets(Collection):
	name = "net"
Nets = Nets()
Nets.does("del")

netlisten_conns = {}
class NetListens(Collection):
	name = "netserver"
NetListens = NetListens()
NetListens.does("del")

net_conns = {}


class NETreceiver(LineReceiver):
	storage = Nets.storage
	storage2 = net_conns

	def lineReceived(self, line):
		line = line.strip().split()
		simple_event(Context(),"net","recv", *(self.name + tuple(line)))

	def down_event(self, external=False):
		simple_event(Context(),"net","disconnect",*self.name)

	def up_event(self, external=False):
		simple_event(Context(),"net","connect",*self.name)

	def not_up_event(self, external=False):
		simple_event(Context(),"net","error",*self.name)

class NETactive(NETreceiver, NetActiveConnector):
	typ = "net_active"
	pass

class NETpassive(NETreceiver, NetPassiveConnector):
	typ = "net_passive"
	pass

class NETlistener(NetListener):
	storage = NetListens.storage

class NETconnect(NetConnect):
	name = ("connect","net")
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
		simple_event(self.ctx, "net","error",*self.dest)


class NETlisten(NetListen):
	name = ("listen","net")
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
	name=("send","net")

class NETconnected(NetConnected):
	storage = Nets.storage
	storage2 = net_conns
	name=("connected","net")

class NETexists(NetExists):
	storage = Nets.storage
	storage2 = net_conns
	name = ("exists","net")

class NETmodule(Module):
	"""\
		Basic TCP connection. Incoming lines are translated to events.
		"""

	info = "Basic line-based TCP access"

	def load(self):
		main_words.register_statement(NETlisten)
		main_words.register_statement(NETconnect)
		main_words.register_statement(NETsend)
		register_condition(NETexists)
		register_condition(NETconnected)
	
	def unload(self):
		main_words.unregister_statement(NETlisten)
		main_words.unregister_statement(NETconnect)
		main_words.unregister_statement(NETsend)
		unregister_condition(NETexists)
		unregister_condition(NETconnected)
	
init = NETmodule
