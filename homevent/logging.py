# *-* coding: utf-8 *-*

"""\
This part of the code defines the logging part of the homevent system.

It consists of a high-priority worker which logs all events, and a
special event which is only used for logging but not seen by any other
part of the system.

"""

from homevent.run import register_worker
from homevent.worker import Worker
from homevent.event import ExceptionEvent,Event

__all__ = ("Logger","register_logger","unregister_logger","log","log_run",
	"TRACE","DEBUG","INFO","WARN","ERROR","PANIC")

loggers = []

TRACE=0
DEBUG=1
INFO=2
WARN=3
ERROR=4
PANIC=5

class Logger(object):
	"""\
		This class implements one particular way to log things.
		"""
	def __init__(self, level):
		self.level = level

	def log(self, event, level=DEBUG):
		if level >= self.level:
			if hasattr(event,"report"):
				for r in event.report(99):
					print event.id,r
			else:
				print str(event)
			print "."

class LogWorker(Worker):
	"""\
		This class is the one which logs everything. Specifically,
		it logs the start of 
		"""
	prio = 0

	def __init__(self):
		super(LogWorker,self).__init__("Logger")

	def report(self,*a,**k):
		"""do nothing."""
		return ()
	def does_event(self,event):
		return True
	def run(self,event):
		"""\
			Run through all loggers. If one of then throws an exception,
			drop the logger and process it.
			"""
		exc = []
		if loggers:
			for l in loggers[:]:
				try:
					l.log(event)
				except Exception,e:
					loggers.remove(l)
					if isinstance(event,ExceptionEvent):
						raise RuntimeError("nested exception",event,e)
					exc.append(e)
		else:
			try:
				Logger(TRACE).log(event)
			except Exception,e:
				if isinstance(event,ExceptionEvent):
					raise RuntimeError("nested exception",event,e)
				exc.append(e)
		if exc:
			from homevent.run import process_event
			for e in exc:
				process_event(ExceptionEvent(e))

class LogEndEvent(Event):
	def __init__(self,event):
		super(LogEndEvent,self).__init__("END",*event.names)
		self.id = event.id
	def report(self, verbose=False):
		yield  "END: "+".".join(self.names[1:])

class LogDoneWorker(LogWorker):
	prio = 99

	def run(self, event):
		super(LogDoneWorker,self).run(LogEndEvent(event))
	def report(self,*a,**k):
		return ("... done.",)

class log_run(Event):
	"""\
		Log executing a single step.
		"""
	def __init__(self,seq,worker=None,event=None):
		if worker:
			super(log_run,self).__init__("WORK",worker.name)
		else:
			super(log_run,self).__init__("WORK","END")
		self.seq = seq
		self.worker = worker
		self.event = event
		if isinstance(worker,LogWorker):
			return
		log(self)
	def report(self, verbose=False):
		if verbose:
			p = "RUN: "
			if self.worker:
				for r in self.worker.report(verbose):
					yield p+r
					p = "   : "
				if p == "   : ":
					p = " at: "
			if self.seq:
				for r in self.seq.report(False):
					yield p+r
					p = "   : "
			if self.event:
				p = " ev: "
				for r in self.event.report(verbose):
					yield p+r
					p = "   : "
		else:
			yield "RUN: "+str(self.worker)

log = LogWorker()
register_worker(log)
log = log.run

register_worker(LogDoneWorker())

def register_logger(logger):
	loggers.append(logger)
def unregister_logger(logger):
	loggers.remove(logger)
