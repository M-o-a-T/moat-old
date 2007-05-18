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
from twisted.internet import reactor,defer

class TriggerHandler(SimpleStatement):
	name=("trigger",)
	doc="send an event"
	long_doc="""\
trigger FOO...
	- creates a FOO... event
"""
	def input(self,w):
		w = w[len(self.name):]
		if not w:
			raise SyntaxError("Events need at least one parameter")
		return process_event(Event(self.ctx,*w))

class WaitHandler(SimpleStatement):
	name=("wait","for")
	doc="delay for N seconds"
	long_doc="""\
wait for FOO...
	- delay processsing for FOO seconds
	  append "s/m/h/d/w" for seconds/minutes/hours/days/weeks
	  # you can do basic +/- calculations (2m - 10s); you do need the spaces
"""
	def input(self,w):
		w = w[len(self.name):]
		print repr(w)
		if not w:
			raise SyntaxError("Timers need a value")
		if len(w) > 2:
			raise SyntaxError("Timers need ONE value",w)
		m = 1
		if len(w) == 1:
			pass
		elif w[1] in ("s","sec","second","seconds"):
			pass
		elif w[1] in ("m","min","minute","minutes"):
			m = 60
		elif w[1] in ("h","hr","hour","hours"):
			m = 60*60
		elif w[1] in ("d","dy","day","days"):
			m = 60*60*24
		elif w[1] in ("w","wk","week","weeks"):
			m = 60*60*24*7
		else:
			raise SyntaxError("unknown unit",w[1])
		w = m * w[0]
		r = defer.Deferred()
		print "S stop"
		def cb():
			print "S go"
			r.callback(None)
		reactor.callLater(w,cb)
		#reactor.callLater(w,r.callback,None)
		return r

from homevent.module import Module
from homevent.logging import log

class EventsModule(Module):
	"""\
		This module contains basic event handling code.
		"""

	info = "Basic event handling"

	def load(self):
		main_words.register_statement(TriggerHandler)
		main_words.register_statement(WaitHandler)
	
	def unload(self):
		main_words.unregister_statement(TriggerHandler)
		main_words.unregister_statement(WaitHandler)

init = EventsModule
