# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2015 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
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
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

"""\
This code does basic timeout handling.

wait: for FOO...
	- waits for FOO seconds

"""

import six

from moat import TESTING
from moat.statement import AttributedStatement, Statement, main_words,\
	global_words
from moat.event import Event
from moat.run import simple_event
from moat.module import Module
from moat.worker import ExcWorker
from moat.times import time_delta, time_until, unixtime,unixdelta, now, humandelta, sleep
from moat.check import Check,register_condition,unregister_condition
from moat.base import Name,SName
from moat.collect import Collection,Collected
from moat.twist import callLater,fix_exception,Jobber,log_wait
from moat.logging import log,log_exc,TRACE
from moat.delay import DelayFor,DelayWhile,DelayUntil,DelayNext,\
	DelayError,DelayDone,DelayCancelled

from gevent.event import AsyncResult
from gevent.lock import Semaphore

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
	soft = False
	storage = Waiters.storage
	_plinger = None

	def __init__(self,parent,name,force,soft):
		self.ctx = parent.ctx
		self.start = now()
		self.force = force
		self.soft = soft
		self._lock = Semaphore()
		try:
			self.parent = parent.parent
		except AttributeError:
			pass
		super(Waiter,self).__init__(name)
		#log(TRACE,"WaitAdded",self.name)
	
	def list(self):
		yield super(Waiter,self)
		yield("start",self.start)
		if self._plinger:
			end=now()+dt.timedelta(0,self.value)
			yield("end",end)
			yield("total", humandelta(end-self.start))
		w = self
		while True:
			w = getattr(w,"parent",None)
			if w is None: break
			n = getattr(w,"displayname",None)
			if n is not None:
				if not isinstance(n,six.string_types):
					n = " ".join(six.text_type(x) for x in n)
			else:
				try:
					if w.args:
						n = six.text_type(w.args)
				except AttributeError:
					pass
				if n is None:
					try:
						if isinstance(w.name,six.string_types):
							n = w.name
						else:
							n = " ".join(six.text_type(x) for x in w.name)
					except AttributeError:
						n = w.__class__.__name__
			if n is not None:
				yield("in",n)

	def info(self):
		return str(self.value)

	def __repr__(self):
		return u"‹%s %s %s›" % (self.__class__.__name__, self.name,self.value)

	def _pling(self,timeout):
		#log(TRACE,"WaitEnter",self.name,self.force,timeout)
		sleep(self.force, timeout, self.name)
		#log(TRACE,"WaitDone Del",self.name)
		assert self._plinger is not None
		self._plinger = None
		super(Waiter,self).delete()
		self.job.set(True)

	def _set_pling(self):
		timeout = unixtime(self.end) - unixtime(now(self.force))
		if timeout <= 0.1:
			timeout = 0.1
		self.stop_job("_plinger")
		self.start_job("_plinger",self._pling, timeout)
		
	def init(self,dest):
		self.job = AsyncResult()
		self.end = dest
		self._set_pling()

	@property
	def value(self):
		if self._plinger is None:
			return None
		return unixtime(self.end)-unixtime(now(self.force))

	def delete(self,ctx=None):
		with log_wait("wait","delete2",self.name):
			with self._lock:
				if self._plinger:
					self.stop_job('_plinger')
					assert self._plinger is None
					#log(TRACE,"WaitDel",self.name)
					super(Waiter,self).delete(ctx=ctx)
					self.job.set(False)

	def retime(self, dest):
		simple_event("wait","update",*self.name,dest=dest, loglevel=TRACE)
		with log_wait("wait","delete1",self.name):
			with self._lock:
				self.end = dest
				self._set_pling()
	
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
	soft = False

	def __init__(self,*a,**k):
		super(WaitHandler,self).__init__(*a,**k)
		global timer_nr
		timer_nr += 1
		self.nr = timer_nr
		self.displayname=("_wait","t"+str(self.nr))

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			self.displayname = SName(event)

		if self.timespec is None:
			raise SyntaxError(u'Usage: wait [name…]: for|until|next ‹timespec›')
		if self.is_update:
			return Waiters[self.displayname].retime(self.timespec())
		w = Waiter(self, self.displayname, self.force, self.soft)
		w.init(self.timespec())
		simple_event("wait","start",*w.name, end_time=ixtime(w.end,self.force), loglevel=TRACE)
		try:
			if w.job:
				r = w.job.get()
			else:
				r = True
		except Exception as ex:
			simple_event("wait","error", *w.name, time=tm,loglevel=TRACE)

			fix_exception(ex)
			log_exc(msg=u"Wait %s died:"%(self.name,), err=ex, level=TRACE)
			raise
		else:
			tm = ixtime(now(self.force),self.force)
			if r:
				simple_event("wait","done", *w.name, loglevel=TRACE)
			else:
				simple_event("wait","cancel", *w.name, loglevel=TRACE)
			ctx.wait = tm
			if not r and not self.soft:
				raise DelayCancelled(w)
		finally:
			w.delete()

		
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

class WaitSoft(Statement):
	name = "soft"
	doc = "don't abort when this waiter is canceled"
	long_doc="""\
Blocks usually are abother when a waiter in them is canceled.
This statement causes the block to continue instead.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			raise SyntaxError('Usage: soft')
		self.parent.soft = True

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
WaitHandler.register_statement(WaitSoft)

class WaitModule(Module):
	"""\
		This module contains the handlers for explicit delays.
		"""

	info = "Delay handling"

	def load(self):
		main_words.register_statement(WaitHandler)
		main_words.register_statement(VarWaitHandler)
		register_condition(Waiters.exists)
	
	def unload(self):
		main_words.unregister_statement(WaitHandler)
		main_words.unregister_statement(VarWaitHandler)
		unregister_condition(Waiters.exists)

init = WaitModule
