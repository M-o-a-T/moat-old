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

"""\
This code does basic event mongering.

trigger FOO...
	- sends the FOO... event

"""

from homevent.statement import Statement, AttributedStatement, main_words
from homevent.event import Event
from homevent.run import process_event, run_event
from homevent.context import Context
from homevent import logging
from homevent.twist import Jobber

import gevent

class TriggerHandler(AttributedStatement,Jobber):
	name="trigger"
	doc="send an event"
	long_doc="""\
trigger FOO...
	- creates a FOO... event. Errors handling the event are reported
	  asynchronously.
"""

	loglevel = None
	recurse = None
	sync = False

	def run(self,ctx,**k):
		if self.loglevel is not None:
			ctx = ctx(loglevel=self.loglevel)
		event = self.params(ctx)
		if self.recurse:
			event.ctx = ctx._trim()
		if not event:
			raise SyntaxError("Events need at least one parameter")

		if self.sync:
			process_event(event)
		else:
			self.start_job("job",run_event,event)
			# TODO: some sort of global job list
			# so that they can be stopped when ending the program

@TriggerHandler.register_statement
class TriggerLog(Statement):
	name = "log"
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
			except AttributeError:
				raise SyntaxError(u'Usage: log LEVEL')
			else:
				self.parent.loglevel = level
		else:
			raise SyntaxError(u'Usage: log LEVEL')

@TriggerHandler.register_statement
class TriggerRecurse(Statement):
	name = "recursive"
	doc = "mark the execution context as recursive"
	long_doc=u"""\
recursive
	Mark the event as one that might cause itself.
	Without this statement, a long environment chain
	will be created which ultimately causes a crash.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		lo = hi = None
		if len(event) == 0:
			self.parent.recurse = True
		else:
			raise SyntaxError(u'Usage: recursive')

@TriggerHandler.register_statement
class TriggerSync(Statement):
	name = "sync"
	doc = "execute the event synchronously"
	long_doc=u"""\
sync
	The event handler is waited for. Errors are propagated to the caller.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		lo = hi = None
		if len(event) == 0:
			self.parent.sync = True
		else:
			raise SyntaxError(u'Usage: sync')



from homevent.module import Module

class TriggerModule(Module):
	"""\
		This module contains basic event handling code.
		"""

	info = "Basic event handling"

	def load(self):
		main_words.register_statement(TriggerHandler)
	
	def unload(self):
		main_words.unregister_statement(TriggerHandler)

init = TriggerModule
