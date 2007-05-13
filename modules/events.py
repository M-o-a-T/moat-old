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
		process_event(Event(self.ctx,*w))

from homevent.module import Module
from homevent.logging import log

class EventsModule(Module):
	"""\
		This module contains basic event handling code.
		"""

	info = "Basic event handling"

	def load(self):
		main_words.register_statement(TriggerHandler)
	
	def unload(self):
		main_words.unregister_statement(TriggerHandler)

init = EventsModule
