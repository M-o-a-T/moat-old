# -*- coding: utf-8 -*-
##BP
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
from __future__ import division,absolute_import

"""\
This code does basic event mongering.

trigger FOO...
	- sends the FOO... event

"""

from moat.statement import Statement, AttributedStatement, main_words
from moat.event import Event
from moat.run import process_event, run_event
from moat.context import Context
from moat import logging
from moat.twist import Jobber

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
	vars = None

	def __init__(self,*a,**k):
		self.vars = {}
		super(TriggerHandler,self).__init__(*a,**k)

	def run(self,ctx,**k):
		if self.loglevel is not None:
			ctx = ctx(loglevel=self.loglevel)
		event = self.params(ctx)
		if not event:
			raise SyntaxError("Events need at least one parameter")
		event.ctx = ctx._trim()

		for k,v in self.vars.items():
			if k[0] == '$':
				k = ctx[k[1:]]
			try:
				if v[0] == '$':
					v = ctx[v[1:]]
			except TypeError: # not a string
				pass
			if k is not None and v is not None:
				setattr(event.ctx, k,v)

		process_event(event)

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

	This currently is a no-op, environment data are always
	flattened.
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

	Currently this is a no-op.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		lo = hi = None
		if len(event) == 0:
			self.parent.sync = True
		else:
			raise SyntaxError(u'Usage: sync')


@TriggerHandler.register_statement
class TriggerParam(Statement):
	name = "param"
	doc = "set an event parameter"
	long_doc=u"""\
param ‹key› ‹val›
	The value ‹val› is attached to the event as ‹key›.

	The event handler will then be able to refer to ‹val› by ‹$key›.
"""
	def run(self,ctx,**k):
		event = self.par(ctx)
		if len(event) != 2:
			raise SyntaxError(u'Usage: param ‹key› ‹val›')
		self.parent.vars[event[0]] = event[1]



from moat.module import Module

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
