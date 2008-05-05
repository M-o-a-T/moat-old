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

from homevent.module import Module
from homevent.logging import log,DEBUG,TRACE,INFO,WARN
from homevent.statement import AttributedStatement,Statement, main_words
from homevent.check import Check,register_condition,unregister_condition
from homevent.run import simple_event,process_failure,register_worker,unregister_worker
from homevent.context import Context
from homevent.event import Event,TrySomethingElse
from homevent.fs20 import handler,register_handler,unregister_handler, \
	PREFIX,PREFIX_TIMESTAMP
from homevent.base import Name,MIN_PRIO
from homevent.worker import ExcWorker
from homevent.reactor import shutdown_event
from homevent.twist import callLater

from twisted.internet import protocol,defer,reactor
from twisted.protocols.basic import _PauseableMixin
from twisted.python import failure
from twisted.internet.error import ProcessExitedAlready
from twisted.internet.serialport import SerialPort

import os

avrs = {}

class FS20common(handler):
	stopped = True
	def __init__(self, name, ctx=Context, timeout=3):
		super(FS20common,self).__init__(ctx=ctx)
		self.name = name
		self.timeout = timeout
		self.timer = None
		self.dbuf = ""
		self.ebuf = ""
		self.lbuf = None
		self.timestamp = None
		self.last_timestamp = None
		self.last_dgram = None
		avrs[self.name] = self
		self.stopped = False
		self.waiting = None

	def connectionMade(self):
		log(DEBUG,"FS20 started",self.name)
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
					db += chr(eval("0x"+e+d))
					e=""
				else:
					e=d
			if e:
				raise ValueError("odd length",data)

			self.datagramReceived(data[0], db, timestamp=self.timestamp)
			self.timestamp = None
		elif data[0] == PREFIX_TIMESTAMP:
			self.timestamp = float(data[1:])
		elif data[0] == "+":
			log("fs20",DEBUG,"fs20 trace "+data)
		else:
			simple_event(Context(),"fs20","unknown","prefix",data[0],data[1:])

	def dataReceived(self, data):
		self._stop_timer()
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

	def inConnectionLost(self):
		log(DEBUG,"FS20 ending",self.name)
		unregister_handler(self)
		pass

	def outConnectionLost(self):
		log(DEBUG,"FS20 ending",self.name)

	def errConnectionLost(self):
		pass

	def processEnded(self, status_object):
		log(DEBUG,"FS20 ended",status_object.value.exitCode, self.name)
		if self.stopped:
			del avrs[self.name]
		else:
			self.do_restart()

	def do_start(self):
		if not self.stopped:
			self._start()
	
	def do_stop(self):
		self.stopped = True
		self.do_kill()
	
	def do_restart(self):
		if not self.stopped:
			callLater(True,5,self.do_start)
		
	def send(self,prefix,data):
		data = prefix+"".join("%02x" % ord(x)  for x in data)
		self.transport.write(data+"\n")
		return defer.succeed(None)


class my_handler(handler):
	def do_kill(self):
		if self.transport:
			try:
				self.transport.signalProcess("KILL")
			except ProcessExitedAlready:
				pass

class FS20cmd(FS20common, protocol.ProcessProtocol, my_handler):
	stopped = True
	def __init__(self, name, cmd, ctx=Context, timeout=3):
		self.cmd = cmd
		super(FS20cmd,self).__init__(name=name,timeout=timeout,ctx=ctx)

	def inConnectionLost(self):
		log(DEBUG,"FS20 ending",self.name)
		unregister_handler(self)
		pass

	def outConnectionLost(self):
		log(DEBUG,"FS20 ending",self.name)

	def errConnectionLost(self):
		pass

	def processEnded(self, status_object):
		log(DEBUG,"FS20 ended",status_object.value.exitCode, self.name)
		if self.stopped:
			del avrs[self.name]
		else:
			self.do_restart()

	def outReceived(self, data):
		self.dataReceived(data)

	def errReceived(self, data):
		self._stop_timer()
		data = (self.ebuf+data).split('\n')
		self.ebuf = data.pop()
		for d in data:
			simple_event(Context(),"fs20","error",*d)
		self._start_timer()

	def _start(self):
		reactor.spawnProcess(self, self.cmd[0], self.cmd, {})
	

class FS20port(FS20common, SerialPort):
	stopped = True
	def __init__(self, name, port, baud=57600, ctx=Context, timeout=3):
		self.port = cmd
		self.baud = baud
		super(FS20cmd,self).__init__(name=name,timeout=timeout,ctx=ctx)
		SerialPort.__init__(self,)

	def inConnectionLost(self):
		log(DEBUG,"FS20 ending",self.name)
		unregister_handler(self)
		pass

	def outConnectionLost(self):
		log(DEBUG,"FS20 ending",self.name)

	def errConnectionLost(self):
		pass

	def processEnded(self, status_object):
		log(DEBUG,"FS20 ended",status_object.value.exitCode, self.name)
		if self.stopped:
			del avrs[self.name]
		else:
			self.do_restart()

	def outReceived(self, data):
		self.dataReceived(data)

	def errReceived(self, data):
		self._stop_timer()
		data = (self.ebuf+data).split('\n')
		self.ebuf = data.pop()
		for d in data:
			simple_event(Context(),"fs20","error",*d)
		self._start_timer()

	def _start(self):
		reactor.spawnProcess(self, self.cmd[0], self.cmd, {})
	

class FS20avr(AttributedStatement):
	name = ("fs20","avr")
	doc = "AVR-based FS20 transceiver"
	long_doc="""\
fs20 avr ‹name…›
  - declare an external device or process that understands FS20 datagrams.
"""

	cmd = None
	port = None
	baud = None

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 1:
			raise SyntaxError(u"Usage: fs20 avr ‹name…›")

		name = Name(event)
		if name in avrs:
			raise RuntimeError(u"‹%s› is already defined" % (name,))
		
		if if self.cmd is not None:
			if self.port is not None:
				raise SyntaxError(u"You cannot use 'port' and 'cmd' at the same time.")
			FS20port(name=name, port=self.port, baud=self.baud, ctx=ctx).do_start()

		else:
			if self.port is not None:
				raise SyntaxError(u"requires a 'cmd' or 'port' subcommand")

			FS20cmd(name=name, cmd=self.cmd, ctx=ctx).do_start()



class FS20listavr(Statement):
	name = ("list","fs20","avr")
	doc = "list external FS20 transceivers"
	long_doc="""\
list fs20 avr
  - List known FS20 transceivers.
    With a name as parameter, list details for that device.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 1:
			for b in avrs.itervalues():
				print >>self.ctx.out,b.name
		else:
			b = avrs[Name(event)]
			print >>self.ctx.out,"name:",b.name
			print >>self.ctx.out,"command:",Name(b.cmd)
			print >>self.ctx.out,"running:","yes" if b.transport else "no"
			print >>self.ctx.out,"stopped:","yes" if b.stopped else "no"
		print >>self.ctx.out,"."


class FS20delavr(Statement):
	name = ("del","fs20","avr")
	doc = "kill of an external fs20 transceiver"
	long_doc="""\
del fs20 avr ‹name…›
  - kill and delete the transceiver.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise syntaxerror(u"usage: del fs20 avr ‹name…›")
		b = avrs[Name(event)]
		b.do_stop()



class FS20cmd(Statement):
	name = ("cmd",)
	doc = "set the command to use"
	long_doc=u"""\
cmd ‹command…›
  - set the actual command to use. Don't forget quoting.
	If you need it to be interpreted by a shell, use
		sh "-c" "your command | pipe | or | whatever"
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise syntaxerror(u"Usage: cmd ‹whatever…›")
		self.parent.cmd = Name(event)
FS20avr.register_statement(FS20cmd)


class FS20cmd(Statement):
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
			self.parent

FS20avr.register_statement(FS20cmd)


class FS20avr_shutdown(ExcWorker):
	"""\
		This worker kills off all processes.
		"""
	prio = MIN_PRIO+1

	def does_event(self,ev):
		return (ev is shutdown_event)
	def process(self,queue,*a,**k):
		for proc in avrs.itervalues():
			proc.do_stop()
		raise TrySomethingElse

	def report(self,*a,**k):
		yield "Shutdown FS20 processes"
		return

FS20avr_shutdown = FS20avr_shutdown("FS20 process killer")



class fs20avr(Module):
	"""\
		Basic fs20 transceiver access.
		"""

	info = "Basic fs20 transceiver"

	def load(self):
		main_words.register_statement(FS20avr)
		main_words.register_statement(FS20listavr)
		main_words.register_statement(FS20delavr)
		register_worker(FS20avr_shutdown)
	
	def unload(self):
		main_words.unregister_statement(FS20avr)
		main_words.unregister_statement(FS20listavr)
		main_words.unregister_statement(FS20delavr)
		unregister_worker(FS20avr_shutdown)
	
init = fs20avr
