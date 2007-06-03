#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
This code does basic timeout handling.

wait FOO...
	- waits for FOO seconds

"""

from homevent.statement import AttributedStatement, Statement, main_words,\
	global_words
from homevent.event import Event
from homevent.run import process_event
from homevent.logging import log,TRACE
from homevent.module import Module
from homevent.worker import HaltSequence
from time import time
from twisted.python.failure import Failure

from twisted.internet import reactor,defer


timer_nr = 0
waiters={}


class WaitCancelled(RuntimeError):
	"""An error signalling that a wait was killed."""
	pass

class DupWaiterError(RuntimeError):
	"""A waiter with that name already exists"""
	pass

class WaitHandler(AttributedStatement):
	name=("wait",)
	doc="delay for N seconds"
	long_doc="""\
wait FOO...
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
		self.displayname="wait_"+str(self.nr)

	def run(self,ctx,**k):
		event = self.params(ctx)
		w = event[:]
		s = 0
		if not w:
			raise SyntaxError("Timers need a value")
		m = 1
		while w:
			if len(w) == 1:
				pass
			elif w[1] in ("s","sec","second","seconds"):
				w.pop(1)
			elif w[1] in ("m","min","minute","minutes"):
				m = 60
				w.pop(1)
			elif w[1] in ("h","hr","hour","hours"):
				m = 60*60
				w.pop(1)
			elif w[1] in ("d","dy","day","days"):
				m = 60*60*24
				w.pop(1)
			elif w[1] in ("w","wk","week","weeks"):
				m = 60*60*24*7
				w.pop(1)
			elif w[1] in ("+","-"):
				pass
			else:
				raise SyntaxError("unknown unit",w[1])
			s += m * w[0]
			w.pop(0)
			if w:
				if w[0] == "+":
					w.pop(0)
					m = 1
				elif w[0] == "-":
					w.pop(0)
					m = -1
				else:
					m = 1 # "1min 59sec"
					
		if self.is_update:
			if s < 0: s = 0
			w = waiters[self.displayname]
			w.retime(s)
			return
			
		if s < 0:
			log(TRACE,"No time out:",s)
			return # no waiting
		log(TRACE,"Timer",self.nr,"::",s)

		r = defer.Deferred()
		if self.displayname in waiters:
			raise DupWaiterError(self.displayname)
		waiters[self.displayname] = self
		self.timer_start=time()
		self.timer_val = s
		self.timer_defer = r
		self.timer_id = reactor.callLater(s, self.doit)
		return r

	def doit(self):
		log(TRACE,"Timeout",self.nr)
		del waiters[self.displayname]
		r = self.timer_defer
		self.timer_defer = None
		r.callback(None)

	def cancel(self, err=WaitCancelled):
		self.timer_id.cancel()
		self.timer_id = None
		self.timer_defer.errback(Failure(err(self)))
	
	def retime(self, timeout):
		self.timer_id.cancel()
		self.timer_val = time()-self.timer_start+timeout
		self.timer_id = reactor.callLater(timeout, self.doit)


class WaitName(Statement):
	name = ("name",)
	doc = "name a wait handler"
	long_doc="""\
This statement assigns a name to a wait statement
(Useful when you want to cancel it later...)
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError('Usage: name "‹text›"')
		self.parent.displayname = event[0]


class WaitCancel(Statement):
	name = ("del","wait")
	doc = "abort a wait handler"
	long_doc="""\
This statement aborts a wait handler.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError('Usage: del wait "‹name›"')
		w = waiters[event[0]]
		w.cancel(err=HaltSequence)

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
				print >>self.ctx.out, w.displayname
			print >>self.ctx.out, "."
		elif len(event) == 1:
			w = waiters[event[0]]
			print  >>self.ctx.out, "Name: ",w.displayname
			print  >>self.ctx.out, "Started: ",w.timer_start
			print  >>self.ctx.out, "Timeout: ",w.timer_val
			print  >>self.ctx.out, "Remaining: ",w.timer_start+w.timer_val-time()
			while True:
				w = getattr(w,"parent",None)
				if w is None: break
				n = getattr(w,"displayname",None)
				if n is None:
					try:
						n = str(w.args)
					except AttributeError:
						pass
					if n is None:
						try:
							n = " ".join(w.name)
						except AttributeError:
							n = w.__class__.__name__
				if n is not None:
					print  >>self.ctx.out, "in: ",n
			print  >>self.ctx.out, "."
				
				
		else:
			raise SyntaxError("Only one name allowed.")


WaitHandler.register_statement(WaitName)
WaitHandler.register_statement(WaitUpdate)


class EventsModule(Module):
	"""\
		This module contains basic event handling code.
		"""

	info = "Basic event handling"

	def load(self):
		main_words.register_statement(WaitHandler)
		main_words.register_statement(WaitCancel)
		global_words.register_statement(WaitList)
	
	def unload(self):
		main_words.unregister_statement(WaitHandler)
		main_words.unregister_statement(WaitCancel)
		global_words.unregister_statement(WaitList)

init = EventsModule
