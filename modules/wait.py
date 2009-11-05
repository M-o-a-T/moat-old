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

from __future__ import division

"""\
This code does basic timeout handling.

wait: for FOO...
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
from homevent.base import Name,SYS_PRIO
from homevent.twist import callLater, reset_slots
from homevent.collect import Collection,Collected

from time import time
import os
from twisted.python import failure
from twisted.internet import reactor,defer
import datetime as dt

timer_nr = 0

class Waiters(Collection):
	name = "wait"
Waiters = Waiters()
Waiters.does("del")

if "HOMEVENT_TEST" in os.environ:
	from test import ixtime
else:
	def ixtime(t):
		return unixtime(t)

class WaitError(RuntimeError):
	def __init__(self,w):
		self.waiter = w
	def __str__(self):
		return self.text % (" ".join(str(x) for x in self.waiter.name),)
	def __unicode__(self):
		return self.text % (" ".join(unicode(x) for x in self.waiter.name),)

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

class Waiter(Collected):
	"""This is the thing that waits."""
	force = False
	storage = Waiters.storage
	def __init__(self,parent,name,force):
		self.ctx = parent.ctx
		self.start = now()
		self.force = force
		try:
			self.parent = parent.parent
		except AttributeError:
			pass
		self.defer = defer.Deferred()
		self.queue = defer.succeed(None)
		self.name = Name(name)
		if self.name in Waiters:
			raise DupWaiterError(self)
	
	def list(self):
		yield("name"," ".join(unicode(x) for x in self.name))
		yield("started",self.start)
		yield("ending",self.end)
		yield("remaining",self.value)
		w = self
		while True:
			w = getattr(w,"parent",None)
			if w is None: break
			n = getattr(w,"displayname",None)
			if n is not None:
				if not isinstance(n,basestring):
					n = " ".join(unicode(x) for x in n)
			else:
				try:
					if w.args:
						n = unicode(w.args)
				except AttributeError:
					pass
				if n is None:
					try:
						if isinstance(w.name,basestring):
							n = w.name
						else:
							n = " ".join(unicode(x) for x in w.name)
					except AttributeError:
						n = w.__class__.__name__
			if n is not None:
				yield("in",n)

	def info(self):
		return str(self.value)

	def __repr__(self):
		return u"‹%s %s %d›" % (self.__class__.__name__, self.name,self.value)

	def _callit(self,_=None):
		self.id = callLater(self.force,self.value, self.doit)

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

		if self.name in Waiters:
			raise DupWaiterError(self)
		Waiters[self.name] = self

		d,e = self._lock()
		d.addCallback(lambda _: process_event(Event(self.ctx,"wait","start",ixtime(self.end),*self.name)))
		d.addCallback(self._callit)
		self._unlock(d,e)
		d.addCallback(lambda _: self.defer)
		return d

	def get_value(self):
		val = self.end-now()
		d = unixdelta(val)
		if d < 0: d = 0
		return d
	value = property(get_value)

	def doit(self):
		d,e = self._lock()
		def did_it(_):
			self.ctx.wait = tm = ixtime(self.end)
			return process_event(Event(self.ctx,"wait","done",tm, *self.name))
		d.addCallback(did_it)
		def done(_):
			self.delete_done()
			self.defer.callback(_)
			self._unlock(d,e)
		d.addCallbacks(done)

	def delete(self,ctx):
		return self.cancel(err=HaltSequence)

	def cancel(self, err=WaitCancelled):
		"""Cancel a waiter."""
		d,e = self._lock()
		if self.defer.called:
			# too late?
			self._unlock(d,e)
			return
		def stoptimer():
			if self.id:
				self.id.cancel()
				self.id = None
		d.addCallback(lambda _: stoptimer())
		d.addCallback(lambda _: process_event(Event(self.ctx,"wait","cancel",ixtime(self.end),*self.name)))
		def errgen(_):
			# If the 'wait cancel' event didn't return a failure, build one.
			return failure.Failure(err(self))
		def done(_):
			# Now make the wait statement itself return with the error.
			self.delete_done()
			self.defer.callback(_)
			self._unlock(d,e)
		d.addCallback(errgen)
		d.addBoth(done)
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
	name=("wait",)
	doc="delay for N seconds"
	long_doc=u"""\
wait [NAME…]: for FOO…
	- delay processsing for FOO seconds
	  append "s/m/h/d/w" for seconds/minutes/hours/days/weeks
	  # you can do basic +/- calculations (2m - 10s); you do need the spaces
"""
	is_update = False
	force = False
	timespec = None

	def __init__(self,*a,**k):
		super(WaitHandler,self).__init__(*a,**k)
		global timer_nr
		timer_nr += 1
		self.nr = timer_nr
		self.displayname=("_wait",self.nr)

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			self.displayname = Name(event)

		if self.timespec is None:
			raise SyntaxError(u'Usage: wait [name…]: for|until|next ‹timespec›')
		if self.is_update:
			return Waiters[self.displayname].retime(self.timespec())
		w = Waiter(self, self.displayname, self.force)
		d = w.init(self.timespec())
		return d

		
class WaitFor(Statement):
	name = ("for",)
	doc = "specify the time to wait"
	long_doc=u"""\
for ‹timespec›
	- specify the absolute time to wait for.
	  N sec / min / hour / day / month / year
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: for ‹timespec…›')

		def delta():
			return time_delta(event)
		self.parent.timespec = delta
	

class WaitUntil(Statement):
	name=("until",)
	doc="delay until some timespec matches"
	long_doc=u"""\
until FOO…
	- delay processsing until FOO matches the current time.
	  Return immediately if it matches already.
	  N sec / min / hour / day / month / year
	  mo/tu/we/th/fr/sa/su: day of week; N mon…sun: month's Nth monday etc
	  N wk: ISO week number
	  negative values go from the end of a period, e.g. month
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: until ‹timespec…›')
		def delta():
			return time_until(event)
		self.parent.timespec = delta
					

class WaitWhile(Statement):
	name=("while",)
	doc="delay while some timespec matches"
	long_doc=u"""\
while FOO…
	- delay processsing while FOO matches the current time
	  N sec / min / hour / day / month / year
	  mo/tu/we/th/fr/sa/su: day of week; N mon…sun: month's Nth monday etc
	  N wk: ISO week number
	  negative values go from the end of a period, e.g. month
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: while ‹timespec…›')
		def delta():
			return time_until(event, invert=True)
		self.parent.timespec = delta
					

class WaitNext(Statement):
	name=("next",)
	doc="delay until some timespec does not match and then matches again"
	long_doc=u"""\
next FOO...
	- delay processsing until the next time FOO matches
	  N sec / min / hour / day / month / year
	  mo/tu/we/th/fr/sa/su: day of week; N mon…sun: month's Nth monday etc
	  N wk: ISO week number
	  negative values go from the end of a period, e.g. month
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: until next ‹timespec…›')

		def delta():
			s = time_until(event, invert=True)
			return time_until(event, now=s)
		self.parent.timespec = delta
					

class WaitDebug(Statement):
	name = ("debug",)
	doc = "Debugging / testing support"
	long_doc=u"""\
debug ‹flags›
	This statement sets internal flags used for debugging.
Known flags:
	force
		Do not optimize this delay away when regression testing.
		No effect in normal use.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: debug ‹flag…›')
		for n in event:
			if n == "force":
				self.parent.force = True
			elif n == "reset":
				reset_slots()
			else:
				raise SyntaxError(u'Flag ‹%s› unknown' % (n,))


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


class ExistsWaiterCheck(Check):
	name=("exists","wait")
	doc="check if a waiter exists at all"
	def check(self,*args):
		if not len(args):
			raise SyntaxError(u"Usage: if exists wait ‹name…›")
		name = Name(args)
		return name in Waiters

class LockedWaiterCheck(Check):
	name=("locked","wait")
	doc="check if a waiter is locked"
	def check(self,*args):
		if not len(args):
			raise SyntaxError(u"Usage: if locked wait ‹name…›")
		name = Name(args)
		return Waiters[name].locked


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
		name = Name(event[1:])
		setattr(self.parent.ctx,var,Waiters[name])


WaitHandler.register_statement(WaitFor)
WaitHandler.register_statement(WaitUntil)
WaitHandler.register_statement(WaitWhile)
WaitHandler.register_statement(WaitNext)
WaitHandler.register_statement(WaitDebug)
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
		for w in Waiters.values():
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
		main_words.register_statement(VarWaitHandler)
		register_condition(ExistsWaiterCheck)
		register_condition(LockedWaiterCheck)
		register_worker(self.worker)
	
	def unload(self):
		main_words.unregister_statement(WaitHandler)
		main_words.unregister_statement(VarWaitHandler)
		unregister_condition(ExistsWaiterCheck)
		unregister_condition(LockedWaiterCheck)
		unregister_worker(self.worker)

init = WaitModule
