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
This code parses a config file.

By itself, it understands nothing whatsoever. This package includes a
"help" command:

	help [word...]
		- show what "word" does

See the homevent.config module and the test/parser.py script
for typical usage.

"""

from homevent.context import Context
from homevent.event import Event
from homevent.base import Name
from homevent.twist import BaseFailure,fix_exception

from twisted.internet import defer
from homevent.geventreactor import waitForDeferred

import sys
import traceback

class InputEvent(Event):
	"""An event that's just a line from the interpreter"""
	def _name_check(self,name):
		pass

	def __str__(self):
		try:
			return "<InputEvent:%s>" % (self.name,)
		except Exception:
			return "<InputEvent> REPORT_ERROR: "+repr(self.name)

	def __unicode__(self):
		try:
			#return u"⌁."+unicode(self.name)
			return unicode(self.name)
		except Exception:
			return u"⌁ REPORT_ERROR: "+repr(self.name)

	def report(self, verbose=False):
		try:
			yield "IEVENT: "+unicode(self.name)
		except Exception:
			yield "IEVENT: REPORT_ERROR: "+repr(self.name)


class Processor(object):
	"""Base class: Process input lines and do something with them."""
	do_prompt = False

	def __init__(self, parent=None, ctx=None):
		self.ctx = ctx or Context()
		self.parent = parent
	
	def lookup(self, args):
		me = self.ctx.words
		event = InputEvent(self.ctx, *args)
		fn = me.lookup(event)
		fn = fn(parent=me, ctx=self.ctx)
		fn.called(event)
		return fn

	def simple_statement(self,args):
		"""\
			A simple statement is a sequence of words. Analyze them.
			"""
		raise NotImplementedError("I cannot understand simple statements.",args)

	def complex_statement(self,args):
		"""\
			A complex statement is a sequence of words followed by a
			colon and at least one sub-statement. This procedure needs
			to reply with a new translator which will (one hopes) accept
			all the sub-statements.

			Needs to return a processor for the sub-statements.
			"""
		raise NotImplementedError("I cannot understand complex statements.",args)
	
	def done(self):
		"""\
			Called on a sub-translator to note that there will be no
			more statements.
			"""
		pass
	
	def error(self,parser,err):
		if isinstance(err,BaseFailure):
			err.raiseException()
		else:
			raise err.__class__,err,sys.exc_info()[2]

class CollectProcessor(Processor):
	"""\
		A processor which simply stores all (sub-)statements, recursively.
		You need to override .store() in order to specify where;
		default is the parent statement.
		"""

	verify = False
	def __init__(self, parent=None, ctx=None, args=None, verify=None):
		super(CollectProcessor,self).__init__(parent=parent, ctx=ctx)
		self.args = args
		self.statements = []
		if verify is not None:
			self.verify = verify
		self.ctx = ctx

	def simple_statement(self,args):
		fn = self.lookup(args)
		if fn.immediate:
			res = fn.run(self.ctx)
			if isinstance(res,defer.Deferred):
				waitForDeferred(res)
			return res
		self.store(fn)

	def complex_statement(self,args):
		fn = self.lookup(args)

		fn.start_block()

		if fn.immediate:
			return RunMe(self,fn)
		else:
			self.store(fn)
			return fn.processor
	
	def done(self):
		return self.parent.end_block()

	def store(self,proc):
		self.parent.add(proc)


class RunMe(object):
	"""\
		This is a wrapper which runs a block as soon as it is finished.
		Needed for complex statements which are marked "immediate", and
		the top-level interpreter loop.
		"""
	def __init__(self,proc,fn):
		self.proc = proc
		self.fn = fn
		self.fnp = fn.processor

	def simple_statement(self,args):
		return self.fnp.simple_statement(args)
	def complex_statement(self,args):
		return self.fnp.complex_statement(args)
	def done(self):
		self.fnp.done()
		res = self.fn.run(self.proc.ctx)
		if isinstance(res,defer.Deferred):
			waitForDeferred(res)

class ImmediateProcessor(CollectProcessor):
	"""\
		A processor which directly executes all (sub-)statements.
		"""

	def __init__(self, parent=None, ctx=None, args=None, verify=False):
		super(ImmediateProcessor,self).__init__(parent=parent, ctx=ctx)

	def simple_statement(self,args):
		fn = self.lookup(args)
		res = fn.run(self.ctx)
		if isinstance(res,defer.Deferred):
			waitForDeferred(res)
		return res

	def complex_statement(self,args):
		fn = self.lookup(args)
		fn.start_block()

		return RunMe(self,fn)

class Interpreter(Processor):
	"""\
		A basic interpreter for the main loop, which runs every
		statement immediately.
		"""
	def __init__(self, ctx=None):
		super(Interpreter,self).__init__(ctx)
		if "words" not in ctx:
			from homevent.statement import global_words
			self.ctx = ctx(words=global_words(ctx=ctx))
		else:
			self.ctx = ctx

	def simple_statement(self,args):
		fn = self.lookup(args)
		try:
			fn.run(self.ctx)
		except Exception as ex:
			fix_exception(ex)
			self.error(self,ex)

	def complex_statement(self,args):
		try:
			fn = self.lookup(args)
		except TypeError,e:
			print >>self.ctx.out,"For",args,"::"
			raise

		fn.start_block()
		return RunMe(self,fn)
	
	def done(self):
		#print >>self.ctx.out,"Exiting"
		pass

class InteractiveInterpreter(Interpreter):
	"""An interpreter which prints a prompt and recovers from errors"""
	do_prompt = True

	def error(self,parser,err):
		from homevent.statement import UnknownWordError

		if isinstance(err,(UnknownWordError,SyntaxError)):
			print >>parser.ctx.out, "ERROR:", err
		else:
			print >>parser.ctx.out, "ERROR:"
			traceback.print_exception(err.__class__,err,sys.exc_info()[2], file=parser.ctx.out)
		if hasattr(parser,'init_state'):
			parser.init_state()
		return
	
	def done(self):
		self.ctx.out.write("\n")
		

