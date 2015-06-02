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
This code does basic configurable event mangling.

on switch *state livingroom *switch:
	send change $state lights livingroom $switch

on switch * * *:
	if neq $2 outside
	if state on alarm internal
	trigger alarm $2

Given the event "switch on livingroom main", this would cause a
"change on lights livingroom main" event if the internal alarm is off.
Otherwise a "alarm livingroom" would be triggered.

"""
import six

from moat.statement import Statement,MainStatementList, main_words
from moat.logging import log, TRACE
from moat.run import MIN_PRIO,MAX_PRIO
from moat.module import Module
from moat.check import register_condition,unregister_condition
from moat.event import TrySomethingElse
from moat.base import Name,SName
from moat.event_hook import OnHandlers, OnEventBase

@six.python_2_unicode_compatible
class BadArgs(RuntimeError):
	def __str__(self):
		return "Mismatch: %s does not fit %s" % (repr(self.args[0]),repr(self.args[1]))

@six.python_2_unicode_compatible
class BadArgCount(RuntimeError):
	def __str__(self):
		return "The number of event arguments does not match"

class OnEventWorker(OnEventBase):
	def process(self, **k):
		super(OnEventWorker,self).process(**k)
		return self.parent.process(**k)

class OnEventHandler(MainStatementList):
	name="on"
	doc="on [event...]: [statements]"
	long_doc="""\
The OnEvent handler executes a statement (or a statement sequence)
when an event occurs.

Syntax:
	on [event...]:
		statement
		...

Every "*foo" in the event description is mapped to the corresponding
"$foo" argument in the list.
"""
	in_sub = False
	prio = (MIN_PRIO+MAX_PRIO)//2+1
	displayname = None

	def grab_args(self,event,ctx):
		### This is a pseudo-clone of grab_event()
		ie = iter(event)
		ia = iter(self.args)
		pos = 0
		while True:
			try: e = six.next(ie)
			except StopIteration: e = StopIteration
			try: a = six.next(ia)
			except StopIteration: a = StopIteration
			if e is StopIteration and a is StopIteration:
				return
			if e is StopIteration or a is StopIteration:
				raise BadArgCount
			if hasattr(a,"startswith") and a.startswith('*'):
				if a == '*':
					pos += 1
					a = str(pos)
				else:
					a = a[1:]
				setattr(ctx,a,e)
			elif str(a) != str(e):
				raise BadArgs(a,e)
		
	def process(self, event=None,**k):
		if event:
			ctx = self.ctx(ctx=event.ctx)
			self.grab_args(event,ctx)
		else:
			ctx = self.ctx()
		return super(OnEventHandler,self).run(ctx)

	def run(self,ctx,**k):
		if self.procs is None:
			raise SyntaxError(u"‹on ...› can only be used as a complex statement")

		OnEventWorker(self, self.args, name=self.displayname,prio=self.prio)

	def start_block(self):
		super(OnEventHandler,self).start_block()
		w = Name(*self.params(self.ctx))
		log(TRACE, "Create OnEvtHandler:", w)
		self.args = w

	def _report(self, verbose=False):
		if self.displayname is not None:
			if isinstance(self.displayname,six.string_types):
				yield "name: "+self.displayname
			else:
				yield "name: "+" ".join(six.text_type(x) for x in self.displayname)
		yield "prio: "+str(self.prio)

		for r in super(OnEventHandler,self)._report(verbose):
			yield r

class OnPrio(Statement):
	name = "prio"
	doc = "prioritize event handler"
	immediate = True
	long_doc="""\
This statement prioritizes an event handler.
If two handlers have the same priority and both match,
the order they (attempt to) run in is undefined.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u"Usage: prio ‹priority›")
		try:
			prio = int(event[0])
		except (ValueError,TypeError):
			raise SyntaxError(u"Usage: prio ‹priority› ⇐ integer priorities only")
		if prio < MIN_PRIO or prio > MAX_PRIO:
			raise ValueError("Priority value (%d): needs to be between %d and %d" % (prio,MIN_PRIO,MAX_PRIO))
		self.parent.prio = prio

class OnName(Statement):
	name = "name"
	doc = "name an event handler"
	immediate = True
	long_doc="""\
This statement assigns a name to an event handler.
(Useful when you want to delete it...)
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u'Usage: name "‹text›"')
		self.parent.displayname = SName(event)

class OnDoc(Statement):
	name = "doc"
	doc = "document an event handler"
	immediate = True
	long_doc="""\
This statement assigns a documentation string to an event handler.
(Useful when you want to document what the thing does ...)
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError(u'Usage: doc "‹text›"')
		self.parent.displaydoc = event[0]

class OnSkip(Statement):
	name = "next handler"
	doc = u"skip ahead to the next on… event handler"
	long_doc="""\
This statement causes processing to skip ahead to the next-higher-priority
event handler.
Commands in the same handler, after this one, are *not* executed.
"""
	def run(self,ctx,**k):
		raise TrySomethingElse()

class OnSkip2(Statement):
	name = "exit handler"
	doc = u"Leave the current event handler"
	long_doc="""\
This statement causes processing of this handler to end.
(This is useful within nested if… statements.)
"""
	def run(self,ctx,**k):
		raise TrySomethingElse()

class OnEventModule(Module):
	"""\
		This module registers the "on EVENT:" handler.
		"""

	info = "the 'on EVENT:' handler"

	def load(self):
		main_words.register_statement(OnEventHandler)
		OnEventHandler.register_statement(OnPrio)
		main_words.register_statement(OnSkip)
		main_words.register_statement(OnSkip2)
		OnEventHandler.register_statement(OnName)
		OnEventHandler.register_statement(OnDoc)
		register_condition(OnHandlers.exists)
	
	def unload(self):
		main_words.unregister_statement(OnEventHandler)
		OnEventHandler.unregister_statement(OnPrio)
		main_words.unregister_statement(OnSkip)
		main_words.unregister_statement(OnSkip2)
		OnEventHandler.unregister_statement(OnName)
		OnEventHandler.unregister_statement(OnDoc)
		unregister_condition(OnHandlers.exists)
	
init = OnEventModule

