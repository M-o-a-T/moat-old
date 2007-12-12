# -*- coding: utf-8 -*-

"""\
This part of the code defines the logging part of the homevent system.

It consists of a high-priority worker which logs all events, and a
special event which is only used for logging but not seen by any other
part of the system.

"""

from homevent.run import register_worker,SYS_PRIO,MIN_PRIO,MAX_PRIO
from homevent.worker import Worker,ExcWorker
from homevent.event import Event
from homevent.context import Context
from twisted.python.failure import Failure
import sys
from traceback import print_exc

__all__ = ("Logger","register_logger","unregister_logger",
	"log","log_run","log_created","log_halted","LogNames",
	"TRACE","DEBUG","INFO","WARN","ERROR","PANIC","NONE")

loggers = []

TRACE=0
DEBUG=1
INFO=2
WARN=3
ERROR=4
PANIC=5
NONE=9

LogNames={
	TRACE:"TRACE",
	DEBUG:"DEBUG",
	WARN:"WARN",
	INFO:"INFO",
	ERROR:"ERROR",
	PANIC:"PANIC",
	NONE:"NONE",
}

levels = {}


def log_level(cls, level=None):
	"""Get/set the logging level for a particular subsystem"""
	ret = levels.get(cls,None)
	if level is not None:
		levels[cls] = level
	return levels


class Logger(object):
	"""\
		This class implements one particular way to log things.
		"""
	def __init__(self, level, out=sys.stdout):
		self.level = level
		self.out = out

	def _log(self, level, data):
		print >>self.out,data

	def log(self, level, *a):
		if level >= self.level:
			self._log(level,u" ".join(unicode(x) for x in a))
			self.flush()

	def log_event(self, event, level):
		if level >= self.level:
			if hasattr(event,"report"):
				for r in event.report(99):
					self._log(level,r)
			else:
				self._log(level,unicode(event))
			self.flush()

	def log_failure(self, err, level=WARN):
		if level >= self.level:
			if err.frames:
				self._log(level,err.getTraceback())
			else:
				self._log(level,unicode(err.value))
	
	def flush(self):
		pass

	def end_logging(self):
		self.flush()
		loggers.remove(self)

class LogWorker(ExcWorker):
	"""\
		This class is the one which logs everything. Specifically,
		it logs the start of every event execution.
		"""
	prio = SYS_PRIO

	def __init__(self):
		super(LogWorker,self).__init__("Logger")

	def report(self,*a,**k):
		"""do nothing."""
		return ()
	def does_event(self,event):
		return True
	def does_failure(self,event):
		return True
	def process(self,event,*a,**k):
		"""\
			Run through all loggers. If one of then throws an exception,
			drop the logger and process it.
			"""
		exc = []
		level = k.get("level",TRACE)
		for l in loggers[:]:
			try:
				l.log_event(event,level=level)
			except Exception,e:
				print >>sys.stderr,"LOGGER CRASH 1"
				print_exc(file=sys.stderr)
				l.end_logging()
				exc.append(sys.exc_info())
		if exc:
			for e in exc:
				log_exc("Logging error", err=e)

	def process_exc(self,err):
		log_exc(err=err,msg="while logging")

def log_exc(msg=None, err=None, level=ERROR):
	if not isinstance(err,Failure):
		if err is None:
			err = sys.exc_info()
		elif not isinstance(err,tuple):
			err = (None,err,None)
		err = Failure(err[1],err[0],err[2])

	for l in loggers[:]:
		if msg:
			try:
				l.log(level,msg)
			except Exception,e:
				print >>sys.stderr,"LOGGER CRASH 2"
				print_exc(file=sys.stderr)
				l.end_logging()
				log_exc("Logger removed",e)
		try:
			l.log_failure(err, level=level)
		except Exception,e:
			print >>sys.stderr,"LOGGER CRASH 3"
			print_exc(file=sys.stderr)
			l.end_logging()
			log_exc("Logger removed",e)

class LogEndEvent(Event):
	def __init__(self,event):
		if isinstance(event,Failure):
			super(LogEndEvent,self).__init__(Context(),"END",event.type.__name__)
		elif not hasattr(event,"ctx"):
			super(LogEndEvent,self).__init__(Context(),"END",event.__class__.__name__)
		else:
			super(LogEndEvent,self).__init__(event.ctx,"END",*event.names)
			self.id = event.id

	def report(self, verbose=False):
		try:
			yield  u"END: "+u"¦".join(unicode(x) for x in self.names[1:])
		except Exception,e:
			print >>sys.stderr,"LOGGER CRASH 4"
			print_exc(file=sys.stderr)
			yield  "END: REPORT_ERROR: "+repr(self.names[1:])

class LogDoneWorker(LogWorker):
	prio = MAX_PRIO+1

	def process(self, event,*a,**k):
		super(LogDoneWorker,self).process(LogEndEvent(event))

	def report(self,*a,**k):
		return ("... done.",)

class log_run(Event):
	"""\
		Log executing a single step.
		"""
	prefix="RUN"
	def __init__(self,seq,worker=None,step=None):
		if worker:
			super(log_run,self).__init__(seq.ctx,"WORK",worker.name)
		else:
			super(log_run,self).__init__(seq.ctx,"WORK","END")
		self.seq = seq
		self.worker = worker
		self.step = step
		if not worker or worker.prio >= MIN_PRIO and worker.prio < MAX_PRIO:
			log_event(self)

	def report(self, verbose=False):
		if verbose:
			p = self.prefix+": "
			if self.step:
				q = u" (step "+unicode(self.step)+u")"
			else:
				q = ""
			if self.worker:
				for r in self.worker.report(verbose):
					yield p+r
					p = " "*len(self.prefix)+": "
				if p == " "*len(self.prefix)+": ":
					p = " "*(len(self.prefix)-2)+"at: "
			if self.seq:
				for r in self.seq.report(False):
					yield p+r+q
					p = " "*len(self.prefix)+": "
					q = ""
				p = " "*(len(self.prefix)-2)+"ev: "
				for r in self.seq.event.report(False):
					yield p+r
					p = " "*len(self.prefix)+": "

		else:
			yield self.prefix+u": "+unicode(self.worker)

class log_halted(Event):
	prefix="HALT"

class log_created(Event):
	"""\
		Log creating an event.
		"""
	def __init__(self,seq):
		super(log_created,self).__init__("NEW",str(seq.iid))
		self.seq = seq
		log_event(self, level=TRACE)
	def report(self, verbose=False):
		if verbose:
			p = "NEW: "
			for r in self.seq.report(verbose):
				yield p+r
				p = "   : "
		else:
			yield "NEW: "+str(self.seq)

def log(level, *a):
	"""\
		Run through all loggers. If one of then throws an exception,
		drop the logger and process it.

		Special feature: You can pass a subsystem name as the very first
		argument. Logging for that subsystem can be enabled by
		log_level(subsys_name, LEVEL).
		"""
	exc = []
	if isinstance(level,basestring):
		lim = levels.get(level,NONE)
		if lim == NONE or lim > level:
			return
		level,b = a[0],level
		a = (b,)+a[1:]
	for l in loggers[:]:
		try:
			l.log(level, *a)
		except Exception,e:
			print >>sys.stderr,"LOGGER CRASH 0"
			print_exc(file=sys.stderr)
			loggers.remove(l)
			exc.append(sys.exc_info())
	if exc:
		for e in exc:
			log_exc("Logging error", err=e)

log_event = LogWorker()
register_worker(log_event)
log_event = log_event.process


register_worker(LogDoneWorker())

def register_logger(logger):
	loggers.append(logger)
def unregister_logger(logger):
	loggers.remove(logger)
