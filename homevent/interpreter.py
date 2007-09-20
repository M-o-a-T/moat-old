#!/usr/bin/python
# -*- coding: utf-8 -*-

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

from twisted.internet import defer
from twisted.python.failure import Failure
import sys

class InputEvent(Event):
	"""An event that's just a line from the interpreter"""
	def _name_check(self,names):
		pass

	def __str__(self):
		try:
			return "⌁."+"¦".join(str(x) for x in self.names)
		except Exception:
			return "⌁ REPORT_ERROR: "+repr(self.names)

	def report(self, verbose=False):
		try:
			yield "IEVENT: "+"¦".join(str(x) for x in self.names)
		except Exception:
			yield "IEVENT: REPORT_ERROR: "+repr(self.names)


class Processor(object):
	"""Base class: Process input lines and do something with them."""
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
		if isinstance(err,Failure):
			err.raiseException()
		else:
			raise err.__class__,e,sys.exc_info()[2]

	def prompt(self, _=None):
		return _

class CollectProcessor(Processor):
	"""\
		A processor which simply stores all (sub-)statements, recursively.
		You need to override .store() in order to specify _where_.
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
			return fn.run(self.ctx)
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
		self.fnp = self.fn.processor

	def simple_statement(self,args):
		return self.fnp.simple_statement(args)
	def complex_statement(self,args):
		return self.fnp.complex_statement(args)
	def done(self):
		d = defer.maybeDeferred(self.fnp.done)
		d.addCallback(lambda _: self.fn.run(self.proc.ctx))
		d.addCallback(lambda _: self.proc.prompt())
		return d

class ImmediateProcessor(CollectProcessor):
	"""\
		A processor which directly executes all (sub-)statements.
		"""

	def __init__(self, parent=None, ctx=None, args=None, verify=False):
		super(ImmediateProcessor,self).__init__(parent=parent, ctx=ctx)

	def simple_statement(self,args):
		fn = self.lookup(args)
		return fn.run(self.ctx)

	def complex_statement(self,args):
		fn = self.lookup(args)
		self.store(fn)
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
		d = defer.maybeDeferred(fn.run,self.ctx)
		d.addBoth(self.prompt)
		return d

	def complex_statement(self,args):
		try:
			fn = self.lookup(args)
		except TypeError,e:
			print >>self.ctx.out,"For",repr(fn),"::"
			raise

		fn.start_block()
		return RunMe(self,fn)
	
	def done(self):
		#print >>self.ctx.out,"Exiting"
		pass

class InteractiveInterpreter(Interpreter):
	"""An interpreter which prints a prompt and recovers from errors"""
	intro = ">> "

	def prompt(self, _=None):
		self.ctx.out.write(self.intro)
		return _
	
	def error(self,parser,err):
		from homevent.statement import UnknownWordError

		err = Failure(err)
		#err.printDetailedTraceback(file=parser.ctx.out)
		#err.printTraceback(file=parser.ctx.out)
		if err.check(UnknownWordError):
			print >>parser.ctx.out, "ERROR:",err.getErrorMessage()
		else:
			print >>parser.ctx.out, "ERROR:"
			err.printBriefTraceback(file=parser.ctx.out)
		parser.init_state()
		self.prompt()
		return

