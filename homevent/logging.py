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
This part of the code defines the logging part of the homevent system.

It consists of a high-priority worker which logs all events, and a
special event which is only used for logging but not seen by any other
part of the system.

"""

from homevent.run import register_worker
from homevent.worker import Worker,ExcWorker,report_
from homevent.event import Event
from homevent.context import Context
from homevent.base import Name,SYS_PRIO,MIN_PRIO,MAX_PRIO
from homevent.twist import fix_exception,print_exception,format_exception
from homevent.collect import Collection,Collected

import gevent
from gevent.queue import JoinableQueue,Full
from gevent.select import select

import sys
import os

__all__ = ("Logger",
	"log","log_run","log_created","log_halted","LogNames",
	"TRACE","DEBUG","INFO","WARN","ERROR","PANIC","NONE")

class Loggers(Collection):
	name = "log"
Loggers = Loggers()
Loggers.can_do("del")

def stop_loggers():
	for l in Loggers.storage.values():
		l.delete()

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
	return ret

logger_nr = 0

class FlushMe(object):
	"""Marker to flush a logger's file"""
	pass

class BaseLogger(Collected):
	"""\
		This class implements one particular way to log things.
		"""
	storage = Loggers.storage
	def __init__(self, level, out=sys.stdout):
		self.level = level
		self.out = out

		global logger_nr
		logger_nr += 1

		if not hasattr(self,"name") or self.name is None:
			self.name = Name(self.__class__.__name__, "x"+str(logger_nr))

		super(BaseLogger,self).__init__()
		self.q = JoinableQueue(100)
		self.job = gevent.spawn(self._writer)

	def _writer(self):
		for r in self.q:
			try:
				if r is None:
					return
				elif r is FlushMe:
					self._flush()
				else:
					self._log(*r)
			finally:
				self.q.task_done()

	# Collection stuff
	def list(self):
		yield ("Name",self.name)
		yield ("Type",self.__class__.__name__)
		yield ("Level",LogNames[self.level])
		yield ("Queue",self.q.qsize())

	def info(self):
		return LogNames[self.level]+": "+self.__class__.__name__

	def delete(self, ctx=None):
		self.q.put(None)
		self.job.join(timeout=1)
		if self.job.dead:
			self.job.kill()
		self.job = None
		self.delete_done()

	def _wlog(self, *a):
		self.q.put(a, block=False)

	def _log(self, *a):
		raise NotImplementedError("You need to override %s._log" % (self.__class__.__name__,))

	def _flush(self):
		pass

	def log(self, level, *a):
		if level >= self.level:
			self._wlog(level,u" ".join(unicode(x) for x in a))
			if "HOMEVENT_TEST" in os.environ:
				self.flush()

	def log_event(self, event, level):
		if level >= self.level:
			for r in report_(event,99):
				self._wlog(level,r)
			if "HOMEVENT_TEST" in os.environ:
				self.flush()

	def log_failure(self, err, level=WARN):
		if level >= self.level:
			self._wlog(level,format_exception(err))
			if "HOMEVENT_TEST" in os.environ:
				self.flush()
	
	def flush(self):
		self.q.put(FlushMe)
		self.q.join()

	def end_logging(self):
		self.flush()
		self.delete()

class Logger(BaseLogger):
	"""\
		This class logs to a file.
		"""
	def __init__(self, level, out=sys.stdout):
		super(Logger,self).__init__(level)
		self.out = out

	def _log(self, level, data):
		if hasattr(self.out,'fileno'):
			select((),(self.out,))
		print >>self.out,data
	
	def _flush(self):
		self.out.flush()

	def list(self):
		for r in super(Loger.self).list():
			yield r
		yield ("Out",repr(self.out))

	def info(self):
		return LogNames[self.level]+" "+repr(self.out)


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
	def process(self,event=None,**k):
		"""\
			Run through all loggers. If one of then throws an exception,
			drop the logger and process it.
			"""
		super(LogWorker,self).process(event=event,**k)
		exc = []
		level = k.get("level",TRACE)
		try:
			if event is None:
				loglevel = NONE
			else:
				loglevel = event.loglevel
			if loglevel == NONE or loglevel > level:
				return
		except AttributeError:
			pass
		subsys = k.get("subsys",None)
		if subsys is not None:
			lim = levels.get(subsys,NONE)
			if lim == NONE or lim > TRACE:
				return

		for l in Loggers.values():
			try:
				l.log_event(event=event,level=level)
			except Exception as e:
				fix_exception(e)
				print >>sys.stderr,"LOGGER CRASH 1"
				print_exception(e,file=sys.stderr)
				l.end_logging()
				exc.append(sys.exc_info())
		if exc:
			for e in exc:
				log_exc("Logging error", err=e)

	def process_exc(self,err):
		log_exc(err=err,msg="while logging")

def log_exc(msg=None, err=None, level=ERROR):
	for l in Loggers.values():
		if msg:
			try:
				l.log(level,msg)
			except Exception as e:
				fix_exception(e)
				print >>sys.stderr,"LOGGER CRASH 2"
				print_exception(e,file=sys.stderr)
				l.end_logging()
				log_exc("Logger removed",e)
		try:
			l.log_failure(err, level=level)
		except Exception as e:
			fix_exception(e)
			print >>sys.stderr,"LOGGER CRASH 3"
			print_exception(e,file=sys.stderr)
			l.end_logging()
			log_exc("Logger removed",e)

class LogEndEvent(Event):
	def __init__(self,event):
		if not hasattr(event,"ctx"):
			super(LogEndEvent,self).__init__(Context(),"END",event.__class__.__name__)
		else:
			super(LogEndEvent,self).__init__(event.ctx,"END",*event.name)
			self.id = event.id

	def report(self, verbose=False):
		try:
			yield  u"END: "+unicode(Name(self.name[1:]))
		except Exception as e:
			fix_exception(e)
			print >>sys.stderr,"LOGGER CRASH 4"
			print_exception(e,file=sys.stderr)
			yield  "END: REPORT_ERROR: "+repr(self.name[1:])

class LogDoneWorker(LogWorker):
	prio = MAX_PRIO+1

	def process(self, event=None,**k):
		super(LogDoneWorker,self).process(event=LogEndEvent(event),**k)

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
				for r in report_(self.seq.event,False):
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
		super(log_created,self).__init__("NEW",str(seq.id))
		self.seq = seq
		lim = levels.get("event",NONE)
		if lim == NONE or lim > TRACE:
			return
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
		lim = levels.get(level, TRACE if "HOMEVENT_TEST" in os.environ else NONE)
		# get the real level from a and add the subsystem name to the front
		b = level
		level = a[0]
		if lim > level:
			return
		a = (b,)+a[1:]

	for l in Loggers.values():
		try:
			l.log(level, *a)
		except Exception as e:
			fix_exception(e)
			print >>sys.stderr,"LOGGER CRASH 0"
			print_exception(e,file=sys.stderr)
			l.delete()
			exc.append(sys.exc_info())
	if exc:
		for e in exc:
			log_exc("Logging error", err=e)

log_event = LogWorker()
register_worker(log_event)
log_event = log_event.process


register_worker(LogDoneWorker())

