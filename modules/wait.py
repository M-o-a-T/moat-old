# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2012, Matthias Urlichs <matthias@urlichs.de>
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

from homevent import TESTING
from homevent.statement import AttributedStatement, Statement, main_words,\
	global_words
from homevent.event import Event
from homevent.run import process_event
from homevent.module import Module
from homevent.worker import ExcWorker
from homevent.times import time_delta, time_until, unixtime,unixdelta, now, humandelta
from homevent.check import Check,register_condition,unregister_condition
from homevent.base import Name,SName
from homevent.collect import Collection,Collected
from homevent.twist import callLater,fix_exception,Jobber
from homevent.logging import log_exc,TRACE
from homevent.delay import DelayFor,DelayWhile,DelayUntil,DelayNext,\
	DelayError,DelayDone,DelayCancelled

import gevent
from gevent.queue import Channel

from time import time
import os
import datetime as dt

timer_nr = 0

class Waiters(Collection):
	name = "wait"
Waiters = Waiters()
Waiters.does("del")

if TESTING:
	from test import ixtime,ttime
	time=ttime
else:
	def ixtime(t,_=None):
		return unixtime(t)

class DupWaiterError(DelayError):
	text = u"A waiter ‹%s› already exists"

class Waiter(Collected,Jobber):
	"""This is the thing that waits."""
	force = False
	storage = Waiters.storage
	_plinger = None
	_running = False
	q = None

	def __init__(self,parent,name,force):
		self.ctx = parent.ctx
		self.start = now()
		self.force = force
		try:
			self.parent = parent.parent
		except AttributeError:
			pass
		super(Waiter,self).__init__(name)
	
	def list(self):
		yield super(Waiter,self)
		yield("started",self.start)
		yield("ending",self.end)
		yield("total", humandelta(self.end-self.start))
		yield("waited", self.start)
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
		try:
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
					return True
				elif cmd == "cancel":
					if self._plinger:
						self._plinger.cancel()
						self._plinger = None
					q.put(None)
					return False
				elif cmd == "update":
					q.put(None)
					self.end = a
					self._set_pling()
				elif cmd == "remain":
					q.put(unixtime(self.end)-unixtime(now(self.force)))
				else:
					q.put(RuntimeError('Unknown command: '+cmd))
		finally:
			self.delete_done()
			q,self.q = self.q,None
			if q is not None:
				while not q.empty():
					q.get()[0].put(StopIteration())

	def init(self,dest):
		self.q = Channel()
		self.end = dest
		self.start_job("job",self._job)

	def _cmd(self,cmd,*a):
		if self.q is None:
			raise DelayDone(self)

		q = Channel()
		self.q.put((q,cmd)+tuple(a))
		res = q.get()
		if isinstance(res,BaseException):
			raise res
		return res

	@property
	def value(self):
		if self.q is None:
			return 0
		if not self._running:
			return "??"
		res = self._cmd("remain")
		if TESTING:
			res = "%.1f" % (res,)
		return res

	def delete(self,ctx=None):
		self._cmd("cancel")

	def cancel(self, err=DelayCancelled):
		"""Cancel a waiter."""
		process_event(Event(self.ctx(loglevel=TRACE),"wait","cancel",ixtime(self.end,self.force),*self.name))
		self._cmd("cancel")

	def retime(self, dest):
		process_event(Event(self.ctx(loglevel=TRACE),"wait","update",dest,*self.name))
		self._cmd("update",dest)

	
class WaitHandler(AttributedStatement):
	name="wait"
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
			self.displayname = SName(event)

		if self.timespec is None:
			raise SyntaxError(u'Usage: wait [name…]: for|until|next ‹timespec›')
		if self.is_update:
			return Waiters[self.displayname].retime(self.timespec())
		w = Waiter(self, self.displayname, self.force)
		w.init(self.timespec())
		process_event(Event(self.ctx(loglevel=TRACE),"wait","start",ixtime(w.end,self.force),*w.name))
		try:
			if w.job:
				r = w.job.get()
			else:
				r = True
		except Exception as ex:
			fix_exception(ex)
			log_exc(msg=u"Wait %s died:"%(self.name,), err=ex, level=TRACE)
			raise
		else:
			tm = ixtime(now(self.force),self.force)
			if r: # don't log 'done' if canceled
				process_event(Event(self.ctx(loglevel=TRACE),"wait","done",tm, *w.name))
			ctx.wait = tm
			if not r:
				raise DelayCancelled(w)

		
class WaitDebug(Statement):
	name = "debug"
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
	name = "update"
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
	name="exists wait"
	doc="check if a waiter exists at all"
	def check(self,*args):
		if not len(args):
			raise SyntaxError(u"Usage: if exists wait ‹name…›")
		name = Name(*args)
		return name in Waiters

class VarWaitHandler(Statement):
	name="var wait"
	doc="assign a variable to report when a waiter will time out"
	long_doc=u"""\
var wait NAME name...
	: $NAME tells how many seconds in the future the wait record ‹name…›
	  will trigger
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		var = event[0]
		name = Name(*event[1:])
		setattr(self.parent.ctx,var,Waiters[name])


WaitHandler.register_statement(DelayFor)
WaitHandler.register_statement(DelayUntil)
WaitHandler.register_statement(DelayWhile)
WaitHandler.register_statement(DelayNext)

if TESTING:
	WaitHandler.register_statement(WaitDebug)
WaitHandler.register_statement(WaitUpdate)


class WaitModule(Module):
	"""\
		This module contains the handlers for explicit delays.
		"""

	info = "Delay handling"

	def load(self):
		main_words.register_statement(WaitHandler)
		main_words.register_statement(VarWaitHandler)
		register_condition(ExistsWaiterCheck)
	
	def unload(self):
		main_words.unregister_statement(WaitHandler)
		main_words.unregister_statement(VarWaitHandler)
		unregister_condition(ExistsWaiterCheck)

init = WaitModule
