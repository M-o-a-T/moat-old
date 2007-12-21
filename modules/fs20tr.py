# -*- coding: utf-8 -*-

"""\
This code implements a primitive FS20 transceiver based on a modified
USB sound interface (or whatever).

"""

from homevent.module import Module
from homevent.logging import log,DEBUG,TRACE,INFO,WARN
from homevent.statement import AttributedStatement,Statement, main_words
from homevent.check import Check,register_condition,unregister_condition
from homevent.run import process_event,process_failure
from homevent.context import Context
from homevent.event import Event
from twisted.internet import protocol,defer,reactor
from twisted.protocols.basic import _PauseableMixin
from twisted.python import failure
from homevent.fs20 import handler,register_handler,unregister_handler
from homevent.base import Name

buses = {}

class FS20recv(protocol.ProcessProtocol, handler):
	def __init__(self, parent, timeout=3):
		self.timeout = timeout
		self.timer = None
		self.parent = parent
		self.dbuf = ""
		self.ebuf = ""

	def connectionMade(self):
		log(DEBUG,"fs20 started",self.parent.name)
		self.transport.closeStdin() # we're not writing anything
		self._start_timer()
	
	def _stop_timer(self):
		if self.timer is not None:
			self.timer.cancel()
			self.timer = None

	def _start_timer(self):
		if self.timer is not None:
			self.timer = reactor.callLater(self.timeout, self.no_data)

	def no_data(self):
		self.timer = None
		self.signalProcess("KILL")
		process_event(Event(Context(),"fs20","wedged",*self.parent.name)).addErrback(process_failure)

	def dataReceived(self,data):
		db = ""
		e = ""
		if len(data)%1:
			raise ValueError("odd length",data)
		for d in data:
			if e:
				db += chr(eval("0x"+e+d))
				e=""
			else:
				e=d
		self.datagramReceived(db)

	def outReceived(self, data):
		self._stop_timer()
		data = (self.dbuf+data).split('\n')
		while len(data) > 1:
			try:
				self.dataReceived(data.pop(0))
			except Exception:
				process_failure()
		self.dbuf = data[0]
		self._start_timer()

	def errReceived(self, data):
		self._stop_timer()
		data = self.ebuf+data
		while True:
			xi = len(data)+1
			try: pi = data.index('\r')
			except ValueError: pi = xi
			try: ei = data.index('\n')
			except ValueError: ei = xi
			if pi==xi and ei==xi:
				break
			if pi < ei:
				data = data[pi+1:]
			else:
				msg = data[:ei]
				data = data[ei+1]
				process_event(Event(Context(),"fs20","error",msg,*self.parent.name)).addErrback(process_failure)

		self.ebuf = data
		self._start_timer()

	def inConnectionLost(self):
		pass

	def outConnectionLost(self):
		log(DEBUG,"fs20 ending",self.parent.name)

	def errConnectionLost(self):
		pass

	def processEnded(self, status_object):
		log(DEBUG,"fs20 ended",status_object.value.exitCode, self.parent.name)
		self.parent.restart()


class FS20receive(AttributedStatement):
	name = ("fs20","receiver")
	doc = "external FS20 receiver"
	long_doc="""\
fs20 receiver ‹name…›
  - declare an external process that listens for FS20 datagrams.
"""

	cmd = None

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 1:
			raise SyntaxError(u"Usage: fs20 receiver ‹name›")
		self.name = Name(event)
		if self.cmd is None:
			raise SyntaxError(u"requires a 'cmd' subcommand")
		self.start()

	def start(self):
		reactor.spawnProcess(FS20recv(self), self.cmd[0], self.cmd, {})
	
	def restart(self):
		reactor.callLater(5,self.start)
		

class FS20xmit(protocol.ProcessProtocol, handler):
	def __init__(self, parent, timeout=3):
		self.timeout = timeout
		self.timer = None
		self.parent = parent
		self.dbuf = ""
		self.ebuf = ""

	def connectionMade(self):
		log(DEBUG,"fs20 started",self.parent.name)
#		if "HOMEVENT_TEST" not in os.environ:
#			self.transport.closeStdout() # we're not reading anything
		self._start_timer()
		register_handler(self)
	
	def _stop_timer(self):
		if self.timer is not None:
			self.timer.cancel()
			self.timer = None

	def _start_timer(self):
		if self.timer is not None:
			self.timer = reactor.callLater(self.timeout, self.no_data)

	def no_data(self):
		self.timer = None
		self.signalProcess("KILL")
		process_event(Event(Context(),"fs20","wedged",*self.parent.name)).addErrback(process_failure)

	def send(self,data):
		data = "".join("%02x" % ord(x)  for x in data)
		self.transport.write(data+"\n")
		return defer.succeed(None)

	def outReceived(self, data):
		data = (self.dbuf+data).split('\n')
		while len(data) > 1:
			log(DEBUG,"FS20 sender output",data.pop(0),self.parent.name)
		self.dbuf = data[0]

	def errReceived(self, data):
		self._stop_timer()
		data = self.ebuf+data
		while True:
			xi = len(data)+1
			try: pi = data.index('\r')
			except ValueError: pi = xi
			try: ei = data.index('\n')
			except ValueError: ei = xi
			if pi==xi and ei==xi:
				break
			if pi < ei:
				data = data[pi+1:]
			else:
				msg = data[:ei]
				data = data[ei+1]
				process_event(Event(Context(),"fs20","error",msg,*self.parent.name)).addErrback(process_failure)

		self.ebuf = data
		self._start_timer()

	def inConnectionLost(self):
		log(DEBUG,"fs20 ending",self.parent.name)
		unregister_handler(self)

	def outConnectionLost(self):
		pass

	def errConnectionLost(self):
		pass

	def processEnded(self, status_object):
		log(DEBUG,"fs20 ended",status_object.value.exitCode, self.parent.name)
		self.parent.restart()


class FS20transmit(AttributedStatement):
	name = ("fs20","sender")
	doc = "external FS20 sender"
	long_doc="""\
fs20 sender ‹name…›
  - declare an external process that can send FS20 datagrams.
"""

	cmd = None

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 1:
			raise SyntaxError(u"Usage: fs20 sender ‹name›")
		self.name = Name(event)
		if self.cmd is None:
			raise SyntaxError(u"requires a 'cmd' subcommand")
		self.start()

	def start(self):
		reactor.spawnProcess(FS20xmit(self), self.cmd[0], self.cmd, {})
	
	def restart(self):
		reactor.callLater(5,self.start)
		

class FS20cmd(Statement):
	name = ("cmd",)
	doc = "Set the command to use"
	long_doc=u"""\
cmd ‹command…›
  - set the actual command to use. Don't forget quoting.
	If you need it to be interpreted by a shell, use
		sh "-c" "your command | pipe | or | whatever"
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u"Usage: cmd ‹whatever…›")
		self.parent.cmd = Name(event)
FS20receive.register_statement(FS20cmd)
FS20transmit.register_statement(FS20cmd)


class fs20tr(Module):
	"""\
		Basic fs20 transceiver access.
		"""

	info = "Basic fs20 transceiver"

	def load(self):
		main_words.register_statement(FS20receive)
		main_words.register_statement(FS20transmit)
	
	def unload(self):
		main_words.unregister_statement(FS20receive)
		main_words.unregister_statement(FS20transmit)
	
init = fs20tr
