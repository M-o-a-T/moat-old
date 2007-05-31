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
from homevent.statement import ComplexStatement


class InputEvent(Event):
	"""An event that's just a line from the interpreter"""
	def __str__(self):
		try:
			return "⌁."+"¦".join(self.names)
		except Exception:
			return "⌁ REPORT_ERROR: "+repr(self.names)

	def report(self, verbose=False):
		try:
			yield "IEVENT: "+"¦".join(self.names)
		except Exception:
			yield "IEVENT: REPORT_ERROR: "+repr(self.names)


class Processor(object):
	"""Base class: Process input lines and do something with them."""
	def __init__(self, parent=None, ctx=None):
		self.ctx = ctx or Context()
		self.parent = parent
	
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

class CollectProcessorBase(Processor):
	"""\
		A processor which simply stores all (sub-)statements, recursively.
		You need to override .store() in order to specify _where_.
		"""

	verify = False
	def __init__(self, parent=None, ctx=None, args=None, verify=None):
		super(CollectProcessorBase,self).__init__(parent=self, ctx=ctx)
		self.args = args
		self.statements = []
		if verify is not None:
			self.verify = verify
		self.ctx = ctx

	def simple_statement(self,args):
		if self.verify:
			self.ctx.words.lookup(args) # discard the result
		self.store(args)

	def complex_statement(self,args):
		"""\
			Note that this code uses a standard CollectProcessor for
			sub-blocks. That is intentional.
			"""
		if verify:
			subdict,args = self.ctx.words.lookup(args)
			ctx = self.ctx(words=subdict)
		else:
			ctx = self.ctx
		subc = CollectProcessor(parent=self.parent, ctx=ctx, args=args)
		self.store(subc)
		return subc

class CollectProcessor(CollectProcessorBase):
	"""A processor which adds all statements to its parent."""
	def store(self,proc):
		self.parent.add(proc)

	def done(self):
		self.parent.end_block()

class ImmediateCollectProcessor(CollectProcessor):
	"""\
		A processor which stores all (sub-)statements, recursively --
		except those that are marked as Immediate, which get executed.
		"""

	def __init__(self, parent=None, ctx=None, args=None, verify=False):
		super(CollectProcessorBase,self).__init__(parent=parent, ctx=ctx)

	def simple_statement(self,args):
		me = self.ctx.words

		event=InputEvent(self.ctx, *args)
		fn = me.lookup(event)
		fn =  fn(parent=me, ctx=self.ctx)
		fn.called(event)
		if fn.immediate:
			return fn.run(self.ctx)
		self.store(fn)

	def complex_statement(self,args):
		me = self.ctx.words
		fn = me.lookup(args)
		fn = fn(parent=me, ctx=self.ctx)
		fn.called(args)
		if fn.immediate:
			try:
				fn.start_block()
			except AttributeError,e:
				return self.ctx._error(e)
			else:
				return fn.processor(parent=fn,ctx=self.ctx(words=fn))
		else:
			subc = ImmediateCollectProcessor(parent=fn, ctx=ctx, args=args)
			self.store(subc)
			return subc

class Interpreter(Processor):
	"""\
		A basic interpreter for the main loop, which runs every
		statement immediately.
		"""
	def __init__(self, ctx=None):
		super(Interpreter,self).__init__(ctx)
		if "words" not in ctx:
			self.ctx = ctx(words=main_words(ctx=ctx))
		else:
			self.ctx = ctx

	def simple_statement(self,args):
		me = self.ctx.words
		fn = me.lookup(args)
		fn = fn(parent=me, ctx=self.ctx)
		fn.called(InputEvent(self.ctx, *args).clone())
		return fn.run(self.ctx)

	def complex_statement(self,args):
		me = self.ctx.words
		fn = me.lookup(args)
		try:
			fn = fn(parent=me, ctx=self.ctx)
		except TypeError,e:
			print >>self.ctx.out,"For",repr(fn),"::"
			raise
		fn.called(args)
		try:
			fn.start_block()
		except AttributeError,e:
			return self.ctx._error(e)
		else:
			return fn.processor ## (parent=fn,ctx=self.ctx(words=fn))
	
	def done(self):
		#print >>self.ctx.out,"Exiting"
		pass

class main_words(ComplexStatement):
	"""\
		This is the top-level dictionary.
		It is named in a strange way as to make the Help output look nice.
		"""
	name = ("Main",)
	doc = "word list:"

