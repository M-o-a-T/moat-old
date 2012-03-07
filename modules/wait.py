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
from homevent.times import time_delta, time_until, unixtime,unixdelta, now, humandelta
from homevent.check import Check,register_condition,unregister_condition
from homevent.base import Name,SYS_PRIO
from homevent.collect import Collection,Collected
from homevent.twist import callLater
from homevent import logging

import gevent
from gevent.queue import Channel,Empty

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
	from test import ixtime,ttime
	time=ttime
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

class WaitDone(WaitError):
	text = u"waiter ‹%s› is finished"

class WaitCancelled(WaitError):
	"""An error signalling that a wait was killed."""
	text = u"Waiter ‹%s› was cancelled"

class DupWaiterError(WaitError):
	text = u"A waiter ‹%s› already exists"

class Waiter(Collected):
	"""This is the thing that waits."""
	force = False
	storage = Waiters.storage
	_plinger = None
	_running = False
	def __init__(self,parent,name,force):
		self.ctx = parent.ctx
		self.start = now()
		self.force = force
		self.q = Channel()
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
		yield super(Waiter,self)
		yield("started",self.start)
		yield("ending",self.end)
		yield("total", humandelta(self.end-self.start))
		yield("waited", humandelta(now()-self.start))
		yield("remaining", self.value)
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
		return u"‹%s %s %s›" % (self.__class__.__name__, self.name,self.value)

	def _pling(self):
		self._plinger = None
		self._cmd("timeout")

	def _set_pling(self):
		timeout = unixtime(self.end) - unixtime(now(self.force))
		if timeout < 0:
			timeout = 0.01
		if self._plinger:
			self._plinger.cancel()
		self._plinger = callLater(self.force, timeout, self._pling)
		
	def _job(self):
		self._set_pling()
		self._running = True
		while True:
			cmd = self.q.get()

			q = cmd[0]
			a = cmd[2] if len(cmd)>2 else None
			cmd = cmd[1]
			if cmd == "timeout":
				assert self._plinger is None
				q.put(None)
				self.q = None
				return True
			elif cmd == "cancel":
				if self._plinger:
					self._plinger.cancel()
					self._plinger = None
				q.put(None)
				self.q = None
				return False
			elif cmd == "update":
				q.put(None)
				self.end = a
				self._set_pling()
			elif cmd == "remain":
				q.put(unixtime(self.end)-unixtime(now(self.force)))
			else:
				q.put(RuntimeError('Unknown command: '+cmd))


	def init(self,dest):
		if self.name in Waiters:
			raise DupWaiterError(self)

		self.q = Channel()
		self.end = dest
		self.job = gevent.spawn(self._job)
		self.job.link(lambda _: self.delete_done())

		Waiters[self.name] = self

	def _cmd(self,cmd,*a):
		if self.q is None:
			raise WaitDone(self)

		q = Channel()
		self.q.put((q,cmd)+tuple(a))
		return q.get()

	@property
	def value(self):
		if self.q is None:
			return 0
		if not self._running:
			return "??"
		return self._cmd("remain")

	def delete(self,ctx):
		self.job.kill()

	def cancel(self, err=WaitCancelled):
		"""Cancel a waiter."""
		process_event(Event(self.ctx(loglevel=logging.TRACE),"wait","cancel",ixtime(self.end),*self.name))
		self._cmd("cancel")

	def retime(self, dest):
		process_event(Event(self.ctx(loglevel=logging.TRACE),"wait","update",dest,*self.name))
		self._cmd("retime",dest)
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
		w.init(self.timespec())
		process_event(Event(self.ctx(loglevel=logging.TRACE),"wait","start",ixtime(w.end),*w.name))
		try:
			r = w.job.get()
		except Exception as ex:
			logging.log_exc(msg=u"Wait %s died:"%(self.name,), err=ex, level=logging.TRACE)
			raise
		else:
			process_event(Event(self.ctx(loglevel=logging.TRACE),"wait","done",time(), *w.name))

		
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
			return time_delta(event, now=now(self.parent.force))
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
			return time_until(event, now=now(self.parent.force))
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
			return time_until(event, invert=True, now=now(self.parent.force))
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
			s = time_until(event, invert=True, now=now(self.parent.force))
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
    def process(self, **k):
		super(Shutdown_Worker_Wait,self).process(**k)
		for w in Waiters.values():
			w.cancel(err=HaltSequence)

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
		register_worker(self.worker)
	
	def unload(self):
		main_words.unregister_statement(WaitHandler)
		main_words.unregister_statement(VarWaitHandler)
		unregister_condition(ExistsWaiterCheck)
		unregister_worker(self.worker)

init = WaitModule
