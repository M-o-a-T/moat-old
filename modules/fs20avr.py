# -*- coding: utf-8 -*-

##
##  Copyright © 2008, Matthias Urlichs <matthias@urlichs.de>
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
This code implements a FS20 transceiver based on a AVR ATmega168
microcontroller.

"""

from homevent.base import Name,MIN_PRIO
from homevent.module import Module
from homevent.logging import log,DEBUG,TRACE,INFO,WARN,ERROR
from homevent.statement import AttributedStatement,Statement, main_words
from homevent.check import Check,register_condition,unregister_condition
from homevent.run import simple_event,process_failure,register_worker,unregister_worker
from homevent.context import Context
from homevent.event import Event,TrySomethingElse
from homevent.fs20 import handler,register_handler,unregister_handler, \
	PREFIX,PREFIX_TIMESTAMP
from homevent.worker import ExcWorker
from homevent.reactor import shutdown_event
from homevent.twist import callLater
from homevent.collect import Collection,Collected

from homevent.net import NetListen,NetConnect,NetSend,NetExists,NetConnected,\
	NetReceiver,NetCommonFactory,DisconnectedError,\
	NetName,NetTo, NetClientFactory,NetServerFactory

from twisted.internet import protocol,reactor,error,defer
from twisted.protocols.basic import _PauseableMixin
from twisted.python import failure
from twisted.internet.error import ProcessExitedAlready
from twisted.internet.serialport import SerialPort

import os

class AVRcommon(handler):
	"""\
		This class implements the protocol for handling AVR messages.
		"""

	stopped = True
	def __init__(self, name, ctx=Context, timeout=3):
		super(AVRcommon,self).__init__(ctx=ctx)
		self.timeout = timeout
		self.timer = None
		self.dbuf = ""
		self.ebuf = ""
		self.lbuf = None
		self.timestamp = None
		self.last_timestamp = None
		self.last_dgram = None
		self.stopped = False
		self.waiting = None

	def connectionMade(self):
		log(DEBUG,"AVR started",self.factory.name)
		self.factory.haveConnection(self)
		self._start_timer()
		register_handler(self)
	
	def _stop_timer(self):
		if self.timer is not None:
			self.timer.cancel()
			self.timer = None

	def _start_timer(self):
		if self.timer is not None:
			self.timer = callLater(True,self.timeout, self.no_data)

	def no_data(self):
		self.timer = None
		self.do_kill()
		simple_event(Context(),"fs20","wedged",*self.name)

	def _dataReceived(self,data):
		db = ""
		e = ""
		if not data: return # empty line
		if data[0] in PREFIX:
			for d in data[1:]:
				if e:
					try:
						db += chr(eval("0x"+e+d))
					except SyntaxError:
						raise SyntaxError("0x"+e+d)
					e=""
				else:
					e=d
			if e:
				log("fs20",WARN,"fs20 odd length "+data)

			self.datagramReceived(data[0], db, timestamp=self.timestamp)
			self.timestamp = None
		elif data[0] == PREFIX_TIMESTAMP:
			self.timestamp = float(data[1:])
		elif data[0] == "P":
			pass # idle
		elif data[0] == "+":
			log("fs20",DEBUG,"fs20 trace "+data)
		else:
			simple_event(Context(),"fs20","unknown","prefix",data[0],data[1:])

	def dataReceived(self, data):
		self._stop_timer()
		data = self.dbuf+data
		while True:
			xi = len(data)+1
			try: pi = data.index('\r')
			except ValueError: pi = xi
			try: ei = data.index('\n')
			except ValueError: ei = xi
			if pi==xi and ei==xi:
				break
			if pi < ei:
				self.lbuf = data[:pi]
				data = data[pi+1:]
			else:
				msg = data[:ei]
				data = data[ei+1:]
				if msg == "" and self.lbuf is not None:
					msg = self.lbuf
					self.lbuf = None
				try:
					self._dataReceived(msg)
				except Exception:
					process_failure()

		self.dbuf = data
		self._start_timer()


	def cont(self, _=None):
		while self.waiting:
			try:
				msg = self.waiting.pop(0)
				log("fs20",DEBUG,msg)
				d = self._dataReceived(msg)
			except Exception:
				process_failure()
			else:
				if d:
					d.addCallback(self.cont)
					return
		self.waiting = None
		self._start_timer()

	def send(self,prefix,data):
		data = prefix+"".join("%02x" % ord(x)  for x in data)
		self.transport.write(data+"\n")
		return defer.succeed(None)


	# standard stuff

	def connectionLost(self,reason):
		log(DEBUG,"AVR ending",self.factory.name,reason)
		unregister_handler(self)

	# process stuff

	def inConnectionLost(self):
		self.connectionLost("in lost")

	def outConnectionLost(self):
		log(DEBUG,"AVR ending",self.name)

	def errConnectionLost(self):
		pass

	def processEnded(self, status_object):
		log(DEBUG,"AVR ended",status_object.value.exitCode, self.factory.name)
		if self.stopped:
			del AVRs[self.name]
		else:
			self.do_restart()


	# my stuff

	def do_start(self):
		if not self.stopped:
			self._start()
	
	def do_stop(self):
		self.stopped = True
		self.do_kill()
	
	def do_restart(self):
		if not self.stopped:
			callLater(True,5,self.do_start)
		
	def do_kill(self):
		raise NotImplementedError("Need to override do_kill()")


#class my_handler(handler):
#	def do_kill(self):
#		if self.transport:
#			try:
#				self.transport.signalProcess("KILL")
#			except ProcessExitedAlready:
#				pass
#
#
#class FS20cmd(FS20common, protocol.ProcessProtocol, my_handler):
#	stopped = True
#	def __init__(self, name, cmd, ctx=Context, timeout=3):
#		self.cmd = cmd
#		super(FS20cmd,self).__init__(name=name,timeout=timeout,ctx=ctx)
#
#	def inConnectionLost(self):
#		log(DEBUG,"FS20 ending",self.name)
#		unregister_handler(self)
#		pass
#
#	def outConnectionLost(self):
#		log(DEBUG,"FS20 ending",self.name)
#
#	def errConnectionLost(self):
#		pass
#
#	def processEnded(self, status_object):
#		log(DEBUG,"FS20 ended",status_object.value.exitCode, self.name)
#		if self.stopped:
#			del avrs[self.name]
#		else:
#			self.do_restart()
#
#	def outReceived(self, data):
#		self.dataReceived(data)
#
#	def errReceived(self, data):
#		self._stop_timer()
#		data = (self.ebuf+data).split('\n')
#		self.ebuf = data.pop()
#		for d in data:
#			simple_event(Context(),"fs20","error",*d)
#		self._start_timer()
#
#	def _start(self):
#		reactor.spawnProcess(self, self.cmd[0], self.cmd, {})
#	
#
#class FS20port(SerialPort):
#	stopped = True
#	def __init__(self, name, port, baud=57600, ctx=Context, timeout=3):
#		self.port = cmd
#		self.baud = baud
#		super(FS20cmd,self).__init__(name=name,timeout=timeout,ctx=ctx)
#		SerialPort.__init__(self,FS20common,port,reactor,57600)
#
#	def connectionLost(self):
#		log(DEBUG,"FS20 ending",self.name)
#		unregister_handler(self)
#		del avrs[self.name]
#		super(FS20port,self).connectionLost()
#
#	def dataReceived(self, data):
#		self._dataReceived(data)
#
#	def _start(self):
#		
#		reactor.spawnProcess(self, self.cmd[0], self.cmd, {})
#	


class AVRs(Collection):
	name = Name("fs20","avr")
AVRs = AVRs()
AVRs.does("del")

avr_conns = {}


class AVRreceiver(AVRcommon,NetReceiver):
	storage = AVRs.storage
	storage2 = avr_conns

class AVRclient_factory(NetClientFactory):
	storage = AVRs.storage
	storage2 = avr_conns

	def down_event(self):
		simple_event(Context(),"fs20","avr","disconnect",*self.name)

	def not_up_event(self):
		simple_event(Context(),"fs20","avr","error",*self.name)

	def up_event(self):
		simple_event(Context(),"fs20","avr","connect",*self.name)

	def protocol(self):
		return AVRreceiver(self.name)

	# Collected stuff
	def info(self):
		return "%s:%s" % (self.host,self.port)
	

class AVRconnect(NetConnect):
	cmd = None
	host = None
	port = None
	baud = None

	name = ("fs20","avr")
	doc = "connect to a TCP port"
	long_doc="""\
fs20 avr NAME :remote host port
  - connect (asynchronously) to the TCP server at the remote port;
	name that connection NAME. Default for port is 54083.
	The system will emit a connection-ready event.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 1:
			raise SyntaxError(u"Usage: fs20 avr ‹name…›")

		name = Name(event)
		if name in AVRs:
			raise RuntimeError(u"‹%s› is already defined" % (name,))
		
		n = (self.cmd is not None) + (self.host is not None) + (self.baud is not None)
		if n == 0:
			raise SyntaxError(u"You need to specify either a serial port, a TCP port, or a command line.")
		if n > 1:
			raise SyntaxError(u"You need to specify either a serial port, a TCP port, or a command line, but not more.")


		if self.cmd:
			AVRcmd(name=name, cmd=self.cmd, ctx=ctx)

		elif self.host:
			f = AVRclient_factory(host=self.host, port=self.port, name=name)
			f.connector = reactor.connectTCP(self.host, self.port, f)

		else:
			AVRhost(name=name, port=self.port, baud=self.baud, ctx=ctx)


class AVRcmd(AttributedStatement):
	name = ("cmd",)
	doc = "pipe through a command"
	long_doc = u"""\
cmd ‹words…›
  - talk to the AVR using this command
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise syntaxerror(u"Usage: cmd ‹whatever…›")
		self.parent.cmd = Name(event)
AVRconnect.register_statement(AVRcmd)


class AVRport(Statement):
	name = ("port",)
	doc = "set the serial port to use"
	long_doc=u"""\
port ‹device› [‹baud›]
  - set the serial port to use. Don't forget quoting.
    The baud rate defaults to 57600.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event) or len(event) > 2:
			raise syntaxerror(u"Usage: port ‹device› [‹baud›]")
		self.parent.port = event[0]
		if len(event) > 1:
			self.parent.baud = int(event[1])
		else:
			self.parent.baud = 57600
AVRconnect.register_statement(AVRport)


class AVRremote(Statement):
	name = ("remote",)
	doc = "set the TCP port to use"
	long_doc=u"""\
remote ‹host› ‹port›?
  - set the remote host and port to use.
    The port defaults to 54083.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event) or len(event) > 2:
			raise syntaxerror(u"Usage: remote ‹host› [‹port›]")
		self.parent.host = event[0]
		if len(event) > 1:
			self.parent.port = int(event[1])
		else:
			self.parent.port = 54083
AVRconnect.register_statement(AVRremote)


class AVRsend(NetSend):
    storage = AVRs.storage
    storage2 = avr_conns
    name=("send","fs20","avr","raw")

class AVRconnected(NetConnected):
	storage = AVRs.storage
	storage2 = avr_conns
	name=("connected","fs20","avr")

class AVRexists(NetExists):
	storage = AVRs.storage
	storage2 = avr_conns
	name = ("exists","fs20","avr")


class FS20avr_shutdown(ExcWorker):
	"""\
		This worker kills off all connections and processes.
		"""
	prio = MIN_PRIO+1

	def does_event(self,ev):
		return (ev is shutdown_event)
	def process(self,queue,*a,**k):
		for proc in AVRs.itervalues():
			proc.do_stop()
		raise TrySomethingElse

	def report(self,*a,**k):
		yield "Shutdown FS20 processes"
		return

FS20avr_shutdown = FS20avr_shutdown("FS20 process killer")



class AVRmodule(Module):
	"""\
		Various ways to talk to an AVR-based on-air module.
		"""

	info = "AVR-based fs20 transceiver"

	def load(self):
		main_words.register_statement(AVRconnect)
		main_words.register_statement(AVRsend)
		register_condition(AVRexists)
		register_condition(AVRconnected)
	
	def unload(self):
		main_words.unregister_statement(AVRconnect)
		main_words.unregister_statement(AVRsend)
		unregister_condition(AVRexists)
		unregister_condition(AVRconnected)
	
init = AVRmodule
