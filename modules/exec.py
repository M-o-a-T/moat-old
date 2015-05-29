# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2015, Matthias Urlichs <matthias@urlichs.de>
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
This code runs arbitrary Python code.

exec some.module.foo bar baz
	- imports some.module and runs foo(bar,baz).
"""

from __future__ import division,absolute_import

import gevent
from homevent.statement import Statement, AttributedStatement, main_words
from homevent.event import Event
from homevent.run import process_event, run_event
from homevent.context import Context
from homevent import logging
from homevent.twist import Jobber
from homevent.module import Module
from homevent.logging import log,DEBUG

from dabroker.util import import_string


class ExecHandler(AttributedStatement,Jobber):
	name="exec"
	doc="run Python code"
	long_doc="""\
exec some.module.FOO bar baz ...
	- Loads "some.module" and calls "foo(CONTEXT, bar,baz,…) there.
"""

	def __init__(self,*a,**k):
		self.vars = {}
		super(ExecHandler,self).__init__(*a,**k)

	def run(self,ctx,**k):
		event = self.params(ctx)
		if not event:
			raise SyntaxError("Events need at least one parameter")

		for k,v in self.vars.items():
			if k[0] == '$':
				k = ctx[k[1:]]
			try:
				if v[0] == '$':
					v = ctx[v[1:]]
			except TypeError: # not an int
				pass
			if k is not None and v is not None:
				setattr(event.ctx, k,v)

		proc = import_string(event[0])
		proc(ctx, *event[1:])

@ExecHandler.register_statement
class ExecParam(Statement):
	name = "param"
	doc = "set a parameter"
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


from homevent.module import Module

class ExecModule(Module):
	"""\
		Contains a function to run arbitrary Python code.
		"""

	info = "call out to Python"

	def load(self):
		main_words.register_statement(ExecHandler)
	
	def unload(self):
		main_words.unregister_statement(ExecHandler)

init = ExecModule
