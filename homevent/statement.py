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
from homevent.logging import log_event,log, TRACE


class UnknownWordError(KeyError):
	def __init__(self,word,where):
		self.word = word
		self.where = where

	def __str__(self):
		return "Cannot find word ‹%s› in ‹%s›" % (" ".join(str(x) for x in self.word), " ".join(self.where.name))

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
		return self.args.clone(ctx,drop=len(self.name))

	def run(self,ctx,**k):
		raise NotImplementedError("You need to override '%s.run' (called with %s)" % (self.__class__.__name__,repr(event)))


class ComplexStatement(Statement):
	"""\
		Base class for handling complex statements. This class has a
		word list which can be used to attach distinct sub-statements.

		A statement may want to be available in both complex and simple
		versions. The difference is that the complex version will have
		calls to start_block() and end_block(). Thus, you need to throw
		an error in .run() if using your statement in simple form does
		not make sense (e.g. a plain "if foo" without sub-statements).

		If you want sub-statements that are executed at runtime (as
		opposed to interpreter time), you want to inherit from
		StatementList instead.
		"""

	__words = None

	def __init__(self,*a,**k):
		super(ComplexStatement,self).__init__(*a,**k)
		self.statements = []

	def __repr__(self):
		if self.__words is None:
			return "‹%s %s›" % (self.__class__.__name__,repr(self.name))
		else:
			return "‹%s %s %d›" % (self.__class__.__name__,repr(self.name),len(self.__words))

	def start_block(self):
		raise NotImplementedError("You need to override '%s.start_block' (called with %s)" % (self.__class__.__name__,repr(self.args)))

	def __getitem__(self,key):
		if self.__words is None:
			raise NotImplementedError("No word list in "+self.__class__.__name__)
		return self.__words[key]

	def lookup(self,args):
		"""\
			Override this if you want to replace the default lookup
			code for sub-statements.
			"""
		
		n = len(args)
		while n >= 0:
			try:
				fn = self[tuple(args[:n])]
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
	
	@classmethod
	def _get_wordlist(self):
		"""Called by Help to get my list of words."""
		return self.__words
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

class AttributedStatement(ComplexStatement):
	"""A statement that can be parameterited."""

	def get_processor(self):
		"""Run sub-statements immediately."""
		from homevent.interpreter import ImmediateProcessor
		return ImmediateProcessor(parent=self, ctx=self.ctx(words=self))
	processor = property(get_processor,doc="which processor works for my content?")

	def start_block(self): pass
	def end_block(self): pass
	def add(self,proc):
		raise RuntimeError("Non-immediate substatement on ‹%s›?" % (" ".join(self.name),))

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

class StatementList(ComplexStatement):
	"""\
		This ComplexStatement encapsulates multiple sub-statements.
		"""
	in_sub = False
	procs = None

	def __repr__(self):
		try:
			return "‹"+self.__class__.__name__+"("+str(self.handler_id)+")›"
		except AttributeError:
			try:
				return "‹"+self.__class__.__name__+" "+str(self.args)+"›"
			except AttributeError:
				return "‹"+self.__class__.__name__+"(?)›"

	def run(self,ctx,**k):
		if self.procs is None:
			raise SyntaxError("This can only be used as a complex statement")
		d = defer.Deferred()
		for proc in self.procs:
			def go(_,p):
				return p.run(ctx)
			d.addCallback(go,proc)
		d.callback(None)
		return d

	def start_block(self):
		self.procs = []

	def add(self,proc):
		log(TRACE, "add", str(proc))
		assert not proc.immediate,"Immediate proc added?"
		self.procs.append(proc)

	def end_block(self):
		pass
	
	def report(self, verbose=False):
		yield "ON "+"¦".join(self.args)
		if not verbose: return
		if self.displayname is not None:
			if isinstance(self.displayname,basestring):
				yield "   name: "+self.displayname
			else:
				yield "   name: "+" ".join(self.displayname)
		yield "   prio: "+str(self.prio)
		pref="proc"
		for p in self.procs:
			try:
				yield "   "+pref+": "+p.__name__+" "+str(p.args)
			except AttributeError:
				yield "   "+pref+": "+repr(p)
			pref="    "
	

class main_words(ComplexStatement):
	"""\
		This is the top-level dictionary.
		It is named in a strange way as to make the Help output look nice.
		"""
	name = ("Main",)
	doc = "word list:"


class global_words(ComplexStatement):
	"""Words that only make sense at top level. It pulls in the main word list."""
	name = ("Global",)
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
		try: return super(global_words,self)._get_wordlist()[key]
		except (KeyError,NotImplementedError,TypeError): pass
		return main_words._get_wordlist()[key]



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


class OffEventHandler(Statement):
	name = ("del","on")
	doc = "forget about an event handler"
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) == 1:
			try: worker = onHandlers[event[0]]
			except KeyError: worker = onHandlerNames[event[0]]
			unregister_worker(worker)
			del onHandlers[worker.handler_id]
			if worker.displayname is not None:
				del onHandlerNames[worker.displayname]
		else:
			raise SyntaxError("Usage: del on ‹handler_id/name›")

class OnListHandler(Statement):
	name = ("list","on")
	doc = "list event handlers"
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			try:
				fl = len(str(max(onHandlers.iterkeys())))
			except ValueError:
				print >>self.ctx.out,"No handlers are defined."
			else:
				for id in sorted(onHandlers.iterkeys()):
					h = onHandlers[id]
					n = "¦".join(h.args)
					if h.displayname is not None:
						if isinstance(h.displayname,basestring):
							n += " ‹"+h.displayname+"›"
						else:
							n += " ‹"+" ".join(h.displayname)+"›"
					print >>self.ctx.out,str(id)+" "*(fl-len(str(id))+1),":",n
		elif len(event) == 1:
			try: h = onHandlers[event[0]]
			except KeyError: h = onHandlerNames[event[0]]
			print >>self.ctx.out, h.handler_id,":","¦".join(h.args)
			if h.displayname is not None:
				if isinstance(h.displayname,basestring):
					print >>self.ctx.out,"Name:",h.displayname
				else:
					print >>self.ctx.out,"Name:"," ".join(h.displayname)
			if hasattr(h,"displaydoc"): print >>self.ctx.out,"Doc:",h.displaydoc
		else:
			raise SyntaxError("Usage: list on ‹handler_id›")


class DoNothingHandler(Statement):
	name = ("do","nothing")
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


