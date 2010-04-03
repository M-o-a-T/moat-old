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
This code does basic event mongering.

trigger FOO...
	- sends the FOO... event

"""

from homevent.statement import Statement, AttributedStatement, main_words
from homevent.event import Event
from homevent.run import process_event, simple_event
from homevent import logging


class TriggerHandler(AttributedStatement):
	name=("trigger",)
	doc="send an event"
	long_doc="""\
trigger FOO...
	- creates a FOO... event. Errors handling the event are reported
	  asynchronously.
"""

	loglevel = None

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not event:
			raise SyntaxError("Events need at least one parameter")
		if self.loglevel is not None:
			ctx = ctx(loglevel=self.loglevel)
		return self.run2(ctx,event)

	def run2(self,ctx,event):
		simple_event(ctx,*event)

class SyncTriggerHandler(TriggerHandler):
	name=("sync","trigger")
	doc="send an event and wait for it"
	long_doc="""\
sync trigger FOO...
	- creates a FOO... event and wait until it is processed. Errors
	  handling the event are propagated to the caller.
"""
	def run2(self,ctx,event):
		return process_event(Event(ctx,*event))

class TriggerLog(Statement):
	name = ("log",)
	doc = "set log level"
	long_doc=u"""\
log LEVEL
	Set the level at which the generated event gets logged.
	See 'help log' for possible levels.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		lo = hi = None
		if len(event) == 1:
			level = event[0].upper()
			try:
				level = getattr(logging,level)
			except KeyError:
				raise SyntaxError(u'Usage: log LEVEL')
			else:
				self.parent.loglevel = level
		else:
			raise SyntaxError(u'Usage: log LEVEL')
TriggerHandler.register_statement(TriggerLog)
SyncTriggerHandler.register_statement(TriggerLog)



from homevent.module import Module

class TriggerModule(Module):
	"""\
		This module contains basic event handling code.
		"""

	info = "Basic event handling"

	def load(self):
		main_words.register_statement(TriggerHandler)
		main_words.register_statement(SyncTriggerHandler)
	
	def unload(self):
		main_words.unregister_statement(TriggerHandler)
		main_words.unregister_statement(SyncTriggerHandler)

init = TriggerModule
