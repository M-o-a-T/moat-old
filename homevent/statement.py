#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
This code holds statement stuff.

By itself, it understands nothing whatsoever. This package includes a
"help" command:

	help [word...]
		- show what "word" does

See the homevent.config module and the test/parser.py script
for typical usage.

"""

import sys
from twisted.internet import reactor,threads,defer
from twisted.python import failure

from homevent.context import Context
from homevent.io import Outputter
from homevent.run import process_failure
from homevent.event import Event


class Statement(object):
	"""\
		Abstract base class for handling statements.
		"""
	name=("unassigned",)
	doc="(unassigned short help text!)"
#	long_doc="""\
#This statement has a help text that has not been overridden.
#Programmer error!
#"""
	immediate = False # don't enqueue this

	def __init__(self,parent=None, ctx=None):
		assert isinstance(self.name,tuple),"Name is "+repr(self.name)
		self.parent = parent
		self.ctx = ctx or Context()
		self.args = None
	
	def __repr__(self):
		if self.args:
			return "‹%s %s›" % (self.__class__.__name__,str(self.args))
		else:
			return "‹%s %s›" % (self.__class__.__name__,repr(self.name))

	@classmethod
	def matches(self,args):
		"""Check if this statement can process this list of words."""
		if len(args) < len(self.name): return False
		return self.name == tuple(args[0:len(self.name)])
	
	def called(self, args):
		"""\
			Tell this statement about the arguments it's called with.
			(This is actually an (Input)Event.)
			"""
		self.args = args
	
	def params(self,ctx):
		"""\
			Internal method: Return the argument list, as modified by
			the context.
			"""
		return self.args.clone(ctx)


class SimpleStatement(Statement):
	"""\
		Base class for simple statements.
		"""

	def run(self,ctx,**k):
		raise NotImplementedError("You need to override '%s.run' (called with %s)" % (self.__class__.__name__,repr(event)))


class ComplexStatement(Statement):
	"""\
		Base class for handling complex statements. This class has a
		word list which can be used to attach meaningful sub-statements.

		A statement may want to be available in both complex and simple
		versions, which means multiply-inheriting from both
		SimpleStatement and ComplexStatement.
		"""
	__words = None

	def __init__(self,*a,**k):
		super(ComplexStatement,self).__init__(*a,**k)
		self.statements = []

	def __repr__(self):
		return "‹%s %s %d›" % (self.__class__.__name__,repr(self.name),len(self.__words))

	def input_complex(self):
		raise NotImplementedError("You need to override '%s.input_complex' (called with %s)" % (self.__class__.__name__,repr(self.args)))

	def lookup(self,args):
		"""\
			Override this if you want to replace the default lookup
			code for sub-statements.
			"""
		if self.__words is None:
			raise NotImplementedError("No word list in "+self.__class__.__name__)
		
		n = len(args)
		while n >= 0:
			try:
				fn = self.__words[tuple(args[:n])]
			except KeyError:
				pass
			else:
				# verify
				if fn.matches(args):
					return fn
			n = n-1

		return self.ctx._error(KeyError("Cannot find word '%s' in '%s'" % (" ".join(str(x) for x in args), " ".join(self.name))))
		
	def get_processor(self):
		"""\
			Returns the translator that should process my substatements.
			By default, returns a CollectProcessor.
			"""
		return CollectProcessor(parent=self, ctx=self.ctx)
	processor = property(get_processor,doc="which processor works for my content?")

	def store(self,s):
		self.statements.append(s)

	def done(self):
		"""\
			Override this if you want a notification that your sub-statement
			is complete.
			"""
		pass
	
	@classmethod
	def _get_wordlist(self):
		"""Called by Help to get my list of words."""
		return self.__words
	@classmethod
	def iterkeys(self):
		return self.__words.iterkeys()
	@classmethod
	def itervalues(self):
		return self.__words.itervalues()
	@classmethod
	def iteritems(self):
		return self.__words.iteritems()

	@classmethod
	def register_statement(self,handler):
		"""\
			Register a handler for a token. handler.run() is called
			with the rest of the words on the line. handler.name is the
			first word on the line, which is used to find the handler.
	
			If the statement is a multi-line section (the stuff after
			colon-ized lines, above), handler.input_block() line is called
			instead. It must return something where its words may be looked
			up in. handler.end_block() will be called when the block is finished,
			if it exists.
			"""
		if self.__words is None:
			self.__words = {}
		if handler.name in self.__words:
			raise ValueError("A handler for '%s' is already registered." % (handler.name,))
		self.__words[handler.name] = handler

	@classmethod
	def unregister_statement(self,handler):
		"""\
			Remove this statement.
			"""
		del self.__words[handler.name]


class IgnoreStatement(SimpleStatement):
	"""Used for error exits"""
	def __call__(self,**k): return self
	def run(self,**k): pass
	def input_complex(self): pass
	def processor(self,**k): return self
	def done(self): pass
	def simple_statement(self,args): pass


