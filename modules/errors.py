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
Error handling.

try:
	do-something
catch KeyError:
	do-something-else
catch:
	do-last-resort

"""

import six

from moat.statement import MainStatementList,Statement, \
	main_words,global_words
from moat.module import Module
from moat.event import RaisedError
from moat.check import check_condition
from moat import logging
from moat.run import process_failure
from moat.twist import fix_exception

import sys

class TryStatement(MainStatementList):
	name="try"
	doc="try: [statements]"
	long_doc="""\
The "try" statement executes a block, but continues after an error.

Syntax:
	try:
		statement
		...

"""
	in_sub = False
	displayname = None
	catch_do = None
	

	def add_catch(self,proc):
		if self.catch_do is None:
			self.catch_do = proc
		else:
			self.catch_do.add_catch(proc)
		
	def run(self,ctx,**k):
		want=True
		if self.procs is None:
			raise SyntaxError(u"‹if ...› can only be used as a complex statement")

		event = self.params(ctx)
		if len(event):
			raise SyntaxError("Usage: try: [Statements]")
		return self._run(ctx,**k)

	def _run(self,ctx,**k):
		try:
			super(TryStatement,self).run(ctx,**k)
		except Exception as err:
			fix_exception(err)
			if self.catch_do:
				self.catch_do.run(ctx(error_=err), **k)
			else:
				process_failure(err)

class CatchStatement(TryStatement):
	name="catch"
	doc="catch: [statements]"
	long_doc="""\
The "catch" statement executes a block only if a previous "try" block
(or the preceding "catch" block) errors out.

Syntax:
	try:
		statement
	catch what ever error got raised:
		statement
	catch ExceptionName:
		statement
	catch:
		statement
		...

Implementation restriction: can't be used at top level. (Wrap with 'block:'.)
"""
	immediate = True

	def start_block(self):
		super(CatchStatement,self).start_block()
		self.arglist = self.params(self.ctx)

	def does_error(self,ctx):
		err = ctx.error_
		ctx = ctx()
		if not isinstance(err,RaisedError):
			if len(self.arglist) > 1:
				return None
			if len(self.arglist):
				if err.__class__.__name__ != self.arglist[0] and not err.__class__.__name__.endswith("."+self.arglist[0]):
					return None
			return ctx
		elif len(self.arglist) == 0:
			pos = 0
			for p in err.params:
				pos += 1
				setattr(ctx,str(pos),p)
			return ctx
		ie = iter(err.params)
		ia = iter(self.arglist)
		pos = 0
		while True:
			try: e = six.next(ie)
			except StopIteration: e = StopIteration
			try: a = six.next(ia)
			except StopIteration: a = StopIteration
			if e is StopIteration and a is StopIteration:
				return ctx
			if e is StopIteration or a is StopIteration:
				return None
			if hasattr(a,"startswith") and a.startswith('*'):
				if a == '*':
					pos += 1
					a = str(pos)
				else: 
					a = a[1:]
				setattr(ctx,a,e)
			elif str(a) != str(e):
				return None

	def run(self,ctx,**k):
		if self.immediate:
			self.immediate = False
			self.parent.procs[-1].add_catch(self)
		else:
			c = self.does_error(ctx)
			if c:
				return self._run(c,**k)
			elif self.catch_do:
				return self.catch_do.run(ctx,**k)
			else:
				raise ctx.error_
	

class ReportStatement(Statement):
	name="log error"
	doc="log error [Severity]"
	long_doc="""\
If running in a "catch" block, this statement logs the current error.

Syntax:
	try:
		statement
	catch:
		log error WARN

"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			level = logging.DEBUG
		elif len(event) == 1:
			try:
				level = getattr(logging,event[0].upper())
			except AttributeError:
				raise SyntaxError("unknown severity",event[0])
		else:
			raise SyntaxError("Usage: log error [severity]")
		logging.log_exc(msg="Logged:", err=ctx.error_, level=level)

class TriggerStatement(Statement):
	name="trigger error"
	doc=u"trigger error NAME…"
	long_doc=u"""\
This command causes an error to be reported.

The names are user-assigned; they'll be accessible as $1…$n in "catch" blocks.
Syntax:
	try:
		trigger error BAD StuffHappened
	catch:
		log WARN "Ouch:" $2

"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			raise SyntaxError(u"Usage: trigger error NAME…")
		err = RaisedError(*event[:])
		logging.log_exc(msg="Triggered:", err=err, level=logging.TRACE)
		raise err

class ErrorsModule(Module):
	"""\
		This module implements the "if ...:" command.
		"""

	info = "try / catch"

	def load(self):
		main_words.register_statement(TryStatement)
		main_words.register_statement(CatchStatement)
		main_words.register_statement(ReportStatement)
		main_words.register_statement(TriggerStatement)
	
	def unload(self):
		main_words.unregister_statement(TryStatement)
		main_words.unregister_statement(CatchStatement)
		main_words.unregister_statement(ReportStatement)
		main_words.unregister_statement(TriggerStatement)
	
init = ErrorsModule
