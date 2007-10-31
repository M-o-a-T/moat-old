#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import division

"""\
This code does basic timeout handling.

wait FOO...
	- waits for FOO seconds

"""

from homevent.statement import AttributedStatement, Statement, main_words,\
	global_words
from homevent.event import Event
from homevent.run import process_event,register_worker,unregister_worker
from homevent.reactor import shutdown_event
from homevent.module import Module
from homevent.worker import HaltSequence,ExcWorker
from homevent.times import time_delta, time_until, unixtime,unixdelta, now
from homevent.check import Check,register_condition,unregister_condition
from homevent.constants import SYS_PRIO
from time import time
import os
from twisted.python.failure import Failure
from twisted.internet import reactor,defer
import datetime as dt

timer_nr = 0
waiters={}

startup = unixtime(now())
def ixtime(t):
	t = unixtime(t)
	if "HOMEVENT_TEST" in os.environ:
		return "%.1f" % (t-startup,)
	return t

class WaitError(RuntimeError):
	def __init__(self,w):
		self.waiter = w
	def __str__(self):
		return self.text % (" ".join(str(x) for x in self.waiter.name),)

class WaitLocked(WaitError):
	text = u"Tried to process waiter ‹%s› while it was locked"

class WaitCancelled(WaitError):
	"""An error signalling that a wait was killed."""
	text = u"Waiter ‹%s› was cancelled"

class DupWaiterError(WaitError):
	text = u"A waiter ‹%s› already exists"


def _trigger(_,d):
	d.callback(None)
	return _

class Waiter(object):
	"""This is the thing that waits."""
	def __init__(self,parent,name):
		self.ctx = parent.ctx
		self.start = now()
		try:
			self.parent = parent.parent
		except AttributeError:
			pass
		self.defer = defer.Deferred()
		self.name = name
		self.queue = defer.succeed(None)
		if self.name in waiters:
			raise DupWaiterError(self)
	
	def __repr__(self):
		return u"‹%s %s %d›" % (self.__class__.__name__, self.name,self.value)

	def _callit(self,_=None):
		self.id = reactor.callLater(self.value, self.doit)

	def _lock(self):
		d = defer.Deferred()
		e = defer.Deferred()

		f = self.queue
		self.queue = e

		f.addBoth(_trigger,d)
		return d,e
	
	def _unlock(self,d,e):
		d.addBoth(_trigger,e)
		

	def init(self,dest):
		self.end = dest
		if self.value <= 0:
			self.defer.callback(None)
			return self.defer

		if self.name in waiters:
			return DupWaiterError(self)
		waiters[self.name] = self

		d,e = self._lock()
		d.addCallback(lambda _: process_event(Event(self.ctx,"wait","start",ixtime(self.end),*self.name)))
		d.addCallback(self._callit)
		self._unlock(d,e)
		d.addCallback(lambda _: self.defer)
		return d

	def get_value(self):
		val = self.end-now()
		d = unixdelta(val)
		if "HOMEVENT_TEST" in os.environ:
			return int(d+1) # otherwise the logs will have timing diffs
		if d < 0: d = 0
		return d
	value = property(get_value)

	def doit(self):
		d,e = self._lock()
		d.addCallback(lambda _: process_event(Event(self.ctx,"wait","done",ixtime(self.end),*self.name)))
		def done(_):
			del waiters[self.name]
			self.defer.callback(_)
			self._unlock(d,e)
		d.addCallbacks(done)

	def cancel(self, err=WaitCancelled):
		d,e = self._lock()
		if self.defer.called:
			self._unlock(d,e)
			return
		def stoptimer():
			if self.id:
				self.id.cancel()
				self.id = None
		d.addCallback(lambda _: stoptimer())
		d.addCallback(lambda _: process_event(Event(self.ctx,"wait","cancel",ixtime(self.end),*self.name)))
		def errgen(_):
			return Failure(err(self))
		def done(_):
			del waiters[self.name]
			self.defer.callback(_)
		d.addCallback(errgen)
		d.addBoth(done)
		self._unlock(d,e)
		return d
	
	def retime(self, dest):
		d,e = self._lock()
		def stoptimer():
			if self.id:
				self.id.cancel()
				self.id = None
		d.addCallback(lambda _: stoptimer())
		def endupdate():
			old_end = self.end
			self.end = dest
		d.addCallback(lambda _: endupdate())
		d.addCallback(lambda _: process_event(Event(self.ctx,"wait","update",ixtime(self.end),*self.name)))
		def err(_):
			self.end = old_end
			self._callit()
			return _
		d.addCallbacks(self._callit, err)
		self._unlock(d,e)
		return d

	
class WaitHandler(AttributedStatement):
	name=("wait","for")
	doc="delay for N seconds"
	long_doc="""\
wait for FOO...
	- delay processsing for FOO seconds
	  append "s/m/h/d/w" for seconds/minutes/hours/days/weeks
	  # you can do basic +/- calculations (2m - 10s); you do need the spaces
"""
	is_update = False

	def __init__(self,*a,**k):
		super(WaitHandler,self).__init__(*a,**k)
		global timer_nr
		timer_nr += 1
		self.nr = timer_nr
		self.displayname=("_wait",self.nr)

	def run(self,ctx,**k):
		event = self.params(ctx)
		return self._waitfor(time_delta(event))
					
	def _waitfor(self,dest):
		if self.is_update:
			return waiters[self.displayname].retime(dest)
			
		w = Waiter(self, self.displayname)
		d = w.init(dest)
		return d

	
class WaitForHandler(WaitHandler):
	name=("wait","until")
	doc="delay until some timespec matches"
	long_doc=u"""\
wait until FOO...
	- delay processsing until FOO matches the current time.
	  Return immediately if it matches already.
	  N sec / min / hour / day / month / year
	  mo/tu/we/th/fr/sa/su: day of week; N mon…sun: month's Nth monday etc
	  N wk: ISO week number
	  negative values go from the end of a period, e.g. month
"""

	def run(self,ctx,**k):
		event = self.params(ctx)

		return self._waitfor(time_until(event))
					

class WaitWhileHandler(WaitHandler):
	name=("wait","while")
	doc="delay while some timespec matches"
	long_doc=u"""\
wait while FOO...
	- delay processsing while FOO matches the current time
	  N sec / min / hour / day / month / year
	  mo/tu/we/th/fr/sa/su: day of week; N mon…sun: month's Nth monday etc
	  N wk: ISO week number
	  negative values go from the end of a period, e.g. month
"""

	def run(self,ctx,**k):
		event = self.params(ctx)

		return self._waitfor(time_until(event, invert=True))
					

class WaitForNextHandler(WaitHandler):
	name=("wait","until","next")
	doc="delay for some timespec does not match and then match again"
	long_doc=u"""\
wait until next FOO...
	- delay processsing until FOO starts matching the current time
	  N sec / min / hour / day / month / year
	  mo/tu/we/th/fr/sa/su: day of week; N mon…sun: month's Nth monday etc
	  N wk: ISO week number
	  negative values go from the end of a period, e.g. month
"""

	def run(self,ctx,**k):
		event = self.params(ctx)

		s = time_until(event, invert=True)
		return self._waitfor(time_until(event, now=s))
					

class WaitName(Statement):
	name = ("name",)
	doc = "name a wait handler"
	long_doc=u"""\
name ‹whatever you want›
	This statement assigns a name to a wait statement.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: name ‹name…›')
		self.parent.displayname = tuple(event)


class WaitCancel(Statement):
	name = ("del","wait")
	doc = "abort a wait handler"
	long_doc=u"""\
del wait ‹whatever the name is›
	This statement aborts a wait handler.
	Everything that depended on the handler's completion will be skipped!
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: del wait ‹name…›')
		w = waiters[tuple(event)]
		return w.cancel(err=HaltSequence)

class WaitUpdate(Statement):
	name = ("update",)
	doc = "change the timeout of an existing wait handler"
	long_doc="""\
This statement updates the timeout of an existing wait handler.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			raise SyntaxError('Usage: update')
		assert hasattr(self.parent,"is_update"), "Not within a wait statement?"
		self.parent.is_update = True


class WaitList(Statement):
	name=("list","wait")
	doc="list of waiting statements"
	long_doc="""\
list wait
	shows a list of running wait statements.
list wait NAME
	shows details for that wait statement.
	
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			for w in waiters.itervalues():
				print >>self.ctx.out, " ".join(str(x) for x in w.name)
			print >>self.ctx.out, "."
		else:
			w = waiters[tuple(event)]
			print  >>self.ctx.out, "Name:"," ".join(str(x) for x in w.name)
			print  >>self.ctx.out, "Started:",w.start
			print  >>self.ctx.out, "Ending:",w.end
			print  >>self.ctx.out, "Remaining:",w.value
			while True:
				w = getattr(w,"parent",None)
				if w is None: break
				n = getattr(w,"displayname",None)
				if n is not None:
					if not isinstance(n,basestring):
						n = " ".join(str(x) for x in n)
				else:
					try:
						n = str(w.args)
					except AttributeError:
						pass
					if n is None:
						try:
							if isinstance(w.name,basestring):
								n = w.name
							else:
								n = " ".join(str(x) for x in w.name)
						except AttributeError:
							n = w.__class__.__name__
				if n is not None:
					print  >>self.ctx.out, "in:",n
			print  >>self.ctx.out, "."

class ExistsWaiterCheck(Check):
	name=("exists","wait")
	doc="check if a waiter exists at all"
	def check(self,*args):
		if not len(args):
			raise SyntaxError(u"Usage: if exists wait ‹name…›")
		name = tuple(args)
		return name in waiters

class LockedWaiterCheck(Check):
	name=("locked","wait")
	doc="check if a waiter is locked"
	def check(self,*args):
		if not len(args):
			raise SyntaxError(u"Usage: if locked wait ‹name…›")
		name = tuple(args)
		return waiters[name].locked


class VarWaitHandler(Statement):
	name=("var","wait")
	doc="assign a variable to report when a waiter will time out"
	long_doc=u"""\
var wait NAME name...
	: $NAME tells how many seconds in the future the wait record ‹name…›
	  will trigger
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		var = event[0]
		name = tuple(event[1:])
		setattr(self.parent.ctx,var,waiters[name])


WaitHandler.register_statement(WaitName)
WaitHandler.register_statement(WaitUpdate)

class Shutdown_Worker_Wait(ExcWorker):
    """\
        This worker kills off all waiters.
        """
    prio = SYS_PRIO+2

    def does_event(self,ev):
        return (ev is shutdown_event)
    def process(self,queue,*a,**k):
		d = defer.succeed(None)
		for w in waiters.values():
			def tilt(_,waiter):
				return waiter.cancel(err=HaltSequence)
			d.addBoth(tilt,w)
		return d

    def report(self,*a,**k):
        return ()


class WaitModule(Module):
	"""\
		This module contains the handlers for explicit delays.
		"""

	info = "Delay handling"
	worker = Shutdown_Worker_Wait("Wait killer")

	def load(self):
		main_words.register_statement(WaitHandler)
		main_words.register_statement(WaitForHandler)
		main_words.register_statement(WaitWhileHandler)
		main_words.register_statement(WaitForNextHandler)
		main_words.register_statement(WaitCancel)
		main_words.register_statement(VarWaitHandler)
		global_words.register_statement(WaitList)
		register_condition(ExistsWaiterCheck)
		register_condition(LockedWaiterCheck)
		register_worker(self.worker)
	
	def unload(self):
		main_words.unregister_statement(WaitHandler)
		main_words.unregister_statement(WaitForHandler)
		main_words.unregister_statement(WaitWhileHandler)
		main_words.unregister_statement(WaitForNextHandler)
		main_words.unregister_statement(WaitCancel)
		main_words.unregister_statement(VarWaitHandler)
		global_words.unregister_statement(WaitList)
		unregister_condition(ExistsWaiterCheck)
		unregister_condition(LockedWaiterCheck)
		unregister_worker(self.worker)

init = WaitModule
