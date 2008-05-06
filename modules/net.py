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

from twisted.internet import protocol,reactor,error
from twisted.protocols.basic import LineReceiver,_PauseableMixin

from homevent.net import NetListen,NetConnect,NetSend,NetExists,NetConnected,\
	NetReceiver,NetCommonFactory,DisconnectedError,\
	NetName,NetTo, NetClientFactory,NetServerFactory

import os

class NETreceiver(NetReceiver):
	pass

class Nets(Collection):
	name = "net"
Nets = Nets()
Nets.can_do("del")

net_conns = {}


class NETcommon_factory(object): # mix-in
	protocol = NETreceiver
	storage = Nets.storage
	storage2 = net_conns

class NETserver_factory(NETcommon_factory, NetServerFactory):
	pass

class NETclient_factory(NETcommon_factory, NetClientFactory):
	pass

class NETconnect(NetConnect):
	name = ("net",)
	client = NETclient_factory
	doc = "connect to a TCP port"
	long_doc="""\
net NAME [host] port
  - connect (asynchronously) to the TCP server at the remote port;
	name that connection NAME. Default for host is localhost.
	The system will emit a connection-ready event.
net [host] port :to NAME…
  - same as above, but use a multi-word name.
"""
	dest = None


class NETlisten(NetListen):
	name = ("listen","net")
	server = NETserver_factory
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


class NETname(NetName):
	pass
NETconnect.register_statement(NETname)
NETlisten.register_statement(NETname)


class NETsend(NetSend):
	storage = Nets.storage
	storage2 = net_conns
	name=("send","net")

class NETto(NetTo):
	pass
NETsend.register_statement(NETto)


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
