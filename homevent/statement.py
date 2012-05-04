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
This code holds statement stuff.

By itself, it understands nothing whatsoever. This package includes a
"help" command:

	help [word...]
		- show what "word" does

See the homevent.config module and the test/parser.py script
for typical usage.

"""

import sys
from homevent.context import Context
from homevent.event import Event,StopParsing
from homevent.logging import log_event,log, TRACE
from homevent.base import Name,SName

from twisted.internet import defer

from homevent.geventreactor import waitForDeferred
import gevent

class UnknownWordError(KeyError):
	def __init__(self,word,where):
		self.word = word
		self.where = where

	def __str__(self):
		return "Cannot find word <%s> in <%s>" % (" ".join(str(x) for x in self.word), " ".join(self.where.name))
	def __unicode__(self):
		return u"Cannot find word ‹%s› in ‹%s›" % (" ".join(unicode(x) for x in self.word), " ".join(self.where.name))

class Statement(object):
	"""\
		Abstract base class for handling statements.
		"""
	name="unassigned"
	doc="(unassigned short help text!)"

#	long_doc="""\
#This statement has a help text that has not been overridden.
#Programmer error!
#"""
	immediate = False # don't enqueue this

	def __init__(self,parent=None, ctx=None):
		self.name = SName(self.name)
		self.parent = parent
		self.ctx = ctx or Context()
		self.args = None
	
	def __repr__(self):
		try:
			if self.args:
				return u"‹%s %s›" % (self.__class__.__name__,self.args)
			else:
				return u"‹%s: %s›" % (self.__class__.__name__,self.name)
		except Exception:
				return u"‹%s ?›" % (self.__class__.__name__,)


	@classmethod
	def matches(self,args):
		"""Check if this statement can process this list of words."""
		if len(args) < len(self.name): return False
		return self.name == Name(*args[0:len(self.name)])
	
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
		return self.args.apply(ctx,drop=len(self.name))

	def par(self,ctx):
		"""\
			Internal method: Return the argument lis, but don't apply
			the context yet.
			"""
		return self.args.dup(ctx,drop=len(self.name))

	def run(self,ctx,**k):
		raise NotImplementedError("You need to override '%s.run' (called with %s)" % (self.__class__.__name__,repr(k)))
	
	def report(self,verbose):
		yield " ".join(unicode(x) for x in self.args)+u" ‹"+self.__class__.__name__+u"›"


class WordLister(type):
	def __init__(cls, name, bases, dct):
		super(WordLister, cls).__init__(name, bases, dct)
		cls._words = {}

class WordAttached(Statement):
	"""\
		Class for attaching word lists to statements.
		The use case is a multiple-inheritance mix-in to a (complex)
		statement which can be configured by its own sub-statement.
		"""

	__metaclass__ = WordLister

	@classmethod
	def __getitem__(self,key):
		for o in self.__mro__:
			if hasattr(o,"_words"):
				try:
					return o._words[key]
				except KeyError:
					pass
		raise KeyError(self,key)

	@classmethod
	def _get_wordlist(self):
		"""Called by Help to get my list of words."""
		wl = {}
		for o in self.__mro__:
			if hasattr(o,"_words"):
				for k,v in o._words.iteritems():
					if k not in wl:
						wl[k] = v
		return wl

	@classmethod
	def iterkeys(self):
		k = self._get_wordlist()
		if k is None: return ()
		return k.iterkeys()
	@classmethod
	def itervalues(self):
		k = self._get_wordlist()
		if k is None: return ()
		return k.itervalues()
	@classmethod
	def iteritems(self):
		k = self._get_wordlist()
		if k is None: return ()
		return k.iteritems()

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
		handler.name = SName(handler.name)

		if handler.name in self._words:
			raise ValueError("A handler for '%s' is already registered. (%s)" % (handler.name,self._words[handler.name]))
		self._words[handler.name] = handler
		return handler

	@classmethod
	def unregister_statement(self,handler):
		"""\
			Remove this statement.
			"""
		del self._words[handler.name]


class ComplexStatement(WordAttached):
	"""\
		Base class for handling complex statements. This class has a
		word list which can be used to attach distinct sub-statements.

		A statement may want to be available in both complex and simple
		versions. The difference is that the complex version will have
		calls to start_block(), at least one add(), and end_block() at
		compile time.
		Thus, you need to throw an error in .run() if using your statement
		in simple form does not make sense (e.g. a plain "if foo" without
		sub-statements).

		If you want sub-statements that are executed at runtime (as
		opposed to interpreter time), you want to inherit from
		StatementList instead.
		"""

	def __init__(self,*a,**k):
		super(ComplexStatement,self).__init__(*a,**k)
		self.statements = []

	def __repr__(self):
		if getattr(self,"_words",None) is None:
			return u"‹%s: %s›" % (self.__class__.__name__,self.name)
		else:
			return u"‹%s: %s %d›" % (self.__class__.__name__,self.name,len(self._words))

	def start_block(self):
		raise NotImplementedError("You need to override '%s.start_block' (called with %s)" % (self.__class__.__name__,repr(self.args)))

	def lookup(self,args):
		"""\
			Override this if you want to replace the default lookup
			code for sub-statements.
			"""
		
		n = len(args)
		while n > 0:
			try:
				fn = self[Name(*args[:n])]
			except KeyError:
				pass
			else:
				# verify
				if fn.matches(args):
					return fn
			n = n-1

		raise UnknownWordError(args,self)
		
	def get_processor(self):
		"""\
			Returns the translator that should process my substatements.
			By default, returns a CollectProcessor.
			"""
		from homevent.interpreter import CollectProcessor
		return CollectProcessor(parent=self, ctx=self.ctx(words=self))
	processor = property(get_processor,doc="which processor works for my content?")

	def store(self,s):
		self.statements.append(s)

	def end_block(self):
		"""\
			Override this if you want a notification that your sub-statement
			is complete.
			"""
		pass
	

class AttributedStatement(ComplexStatement):
	"""A statement that can be parameterized."""

	def get_processor(self):
		"""Run sub-statements immediately."""
		from homevent.interpreter import ImmediateProcessor
		return ImmediateProcessor(parent=self, ctx=self.ctx(words=self))
	processor = property(get_processor,doc="which processor works for my content?")

	def start_block(self): pass
	def end_block(self): pass
	def add(self,proc):
		raise RuntimeError(u"Non-immediate substatement on ‹%s› %s?" % (" ".join(self.name),proc))

class IgnoreStatement(Statement):
	"""Used for error exits"""
	def __call__(self,**k): return self
	def run(self,*a,**k): pass
	def start_block(self): pass
	def processor(self,**k): return self
	def end_block(self): pass
	def simple_statement(self,args): pass


# statement list

class BadArgs(RuntimeError):
	def __str__(self):
		return "Mismatch: %s does not fit %s" % (repr(self.args[0]),repr(self.args[1]))

class BadArgCount(RuntimeError):
	def __str__(self):
		return "The number of event arguments does not match"

_sleep = 0
class StatementList(ComplexStatement):
	"""\
		This ComplexStatement encapsulates multiple sub-statements.
		"""
	in_sub = False
	procs = None

	def __repr__(self):
		try:
			return u"‹"+self.__class__.__name__+"("+unicode(self.handler_id)+u")›"
		except AttributeError:
			try:
				return u"‹"+self.__class__.__name__+" "+unicode(self.args)+u"›"
			except AttributeError:
				return u"‹"+self.__class__.__name__+u"(?)›"

	def run(self,ctx,**k):
		if self.procs is None:
			raise SyntaxError("This can only be used as a complex statement")
		for proc in self.procs:
			res = proc.run(ctx)
			if isinstance(res,defer.Deferred):
				waitForDeferred(res)
			global _sleep
			_sleep += 1
			if _sleep > 100:
				_sleep = 0
				gevent.sleep(0) # give other tasks a chance

	def start_block(self):
		self.procs = []

	def add(self,proc):
		assert not proc.immediate,"Immediate proc added?"
		self.procs.append(proc)

	def end_block(self):
		pass
	
	def report(self, verbose=False):
		for r in super(StatementList,self).report(verbose):
			yield r
		if not verbose: return
		for r in self._report(verbose):
			yield r

	def _report(self, verbose=False):
		if self.procs:
			for p in self.procs:
				pref="step"
				for r in p.report(verbose-1):
					yield pref+": "+r
					pref="    "
	

class main_words(ComplexStatement):
	"""\
		This is the top-level dictionary.
		It is named in a strange way as to make the Help output look nice.
		"""
	name = Name("Main")
	doc = "word list:"


class global_words(ComplexStatement):
	"""Words that only make sense at top level. It pulls in the main word list."""
	name = Name("Global")
	doc = "word list:"

	@classmethod
	def _get_wordlist(self):
		"""Yes, this is inefficient. So? It's not used often."""
		d1 = super(global_words,self)._get_wordlist()
		d2 = main_words._get_wordlist()
		if not d1: return d2
		if d2:
			d1 = d1.copy()
			d1.update(d2)
		return d1

	@classmethod
	def __getitem__(self,key):
		"""This uses a more efficient method. ;-)"""
		try: return super(global_words,self).__getitem__(key)
		except KeyError: pass
		return main_words.__getitem__(key)



class MainStatementList(StatementList):
	"""\
		A Statement list that inherits (some) words that it understands
		from the main word list
		"""
	main = main_words()
	def lookup(self, args):
		try:
			return super(MainStatementList,self).lookup(args)
		except (KeyError,NotImplementedError):
			return self.main.lookup(args)


class DoNothingHandler(Statement):
	name = "do nothing"
	doc = "do not do anything"
	long_doc="""\
This statement does not do anything. It's a placeholder if you want to
explicitly state that some event does not result in any action.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			raise SyntaxError("Usage: do nothing")
		log(TRACE,"NOW: do nothing")


class ExitHandler(Statement):
	name = "exit"
	doc = "stop processing input"
	long_doc="""\
This statement causes the input channel which runs it to terminate.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			raise SyntaxError("Usage: exit")
		raise StopParsing

global_words.register_statement(ExitHandler)


class HelpSubProxy(object):
	def __init__(self,x,name):
		self.x = x
		self.n=name

	@property
	def doc(self): return self.x.doc
	@property
	def long_doc(self): return self.x.long_doc
	@property
	def name(self): return Name(getattr(self.x,self.n))

	def __call__(self): return self
	
class HelpSub(object):
	# help support
	def __getitem__(self,k):
		sname=getattr(self,"helpsubname","name")
		return HelpSubProxy(self.helpsub.__getitem__(k),sname)
	def iteritems(self):
		sname=getattr(self,"helpsubname","name")
		for i,j in self.helpsub.iteritems():
			yield (i,HelpSubProxy(j,sname))

