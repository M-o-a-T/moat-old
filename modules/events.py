#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
This code does basic event mongering.

trigger FOO...
	- sends the FOO... event

"""

from homevent.parser import SimpleStatement, main_words
from homevent.event import Event
from homevent.run import process_event
from homevent.logging import log,TRACE
from homevent.handler import OnEventHandler
from twisted.internet import reactor,defer

class TriggerHandler(SimpleStatement):
	name=("trigger",)
	doc="send an event"
	long_doc="""\
trigger FOO...
	- creates a FOO... event
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		w = event[len(self.name):]
		if not w:
			raise SyntaxError("Events need at least one parameter")
		process_event(Event(self.ctx,*w))

class SyncTriggerHandler(TriggerHandler):
	name=("sync","trigger")
	doc="send an event and wait for it"
	long_doc="""\
sync trigger FOO...
	- creates a FOO... event and wait until it is processed
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		w = event[len(self.name):]
		if not w:
			raise SyntaxError("Events need at least one parameter")
		return process_event(Event(self.ctx,*w))


timer_nr = 0

class WaitHandler(SimpleStatement):
	name=("wait","for")
	doc="delay for N seconds"
	long_doc="""\
wait for FOO...
	- delay processsing for FOO seconds
	  append "s/m/h/d/w" for seconds/minutes/hours/days/weeks
	  # you can do basic +/- calculations (2m - 10s); you do need the spaces
"""
	def __init__(self,*a,**k):
		super(WaitHandler,self).__init__(*a,**k)
		global timer_nr
		timer_nr += 1
		self.nr = timer_nr

	def run(self,ctx,**k):
		event = self.params(ctx)
		w = event[len(self.name):]
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
					
		if s < 0:
			log(TRACE,"No time out:",s)
			return # no waiting
		log(TRACE,"Timer",self.nr,"::",s)
		r = defer.Deferred()
		def doit():
			log(TRACE,"Timeout",self.nr)
			r.callback(None)
		reactor.callLater(s,doit)
		return r


from homevent.module import Module

class EventsModule(Module):
	"""\
		This module contains basic event handling code.
		"""

	info = "Basic event handling"

	def load(self):
		main_words.register_statement(TriggerHandler)
		main_words.register_statement(SyncTriggerHandler)
		main_words.register_statement(WaitHandler)
		OnEventHandler.register_statement(TriggerHandler)
		OnEventHandler.register_statement(SyncTriggerHandler)
		OnEventHandler.register_statement(WaitHandler)
	
	def unload(self):
		main_words.unregister_statement(TriggerHandler)
		main_words.unregister_statement(SyncTriggerHandler)
		main_words.unregister_statement(WaitHandler)
		OnEventHandler.unregister_statement(TriggerHandler)
		OnEventHandler.unregister_statement(SyncTriggerHandler)
		OnEventHandler.unregister_statement(WaitHandler)

init = EventsModule
