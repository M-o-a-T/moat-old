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

from tokenize import generate_tokens
import Queue
from twisted.internet import reactor,threads
from homevent.context import Context

class Processor(object):
	"""Base class: Process input lines and do something with them."""
	def __init__(self, ctx=None):
		self.ctx = ctx or Context()
	
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

	def __init__(self, parent=None, ctx=None, args=None, verify=False):
		super(CollectProcessor,self).__init__(parent=self, ctx=ctx)
		self.args = args
		self.statements = []
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
		subc = CollectProcessor(parent=self, ctx=ctx, args=args)
		self.store(subc)
		return subc

class CollectProcessor(CollectProcessorBase):
	"""A processor which adds all statements to its parent."""
	def store(self,proc):
		self.parent.add(proc)

	def done(self):
		self.parent.done()

class CollectParentProcessor(CollectProcessorBase):
	"""A processor which calls .add() and .done() on its parent."""

class Parser(object):
	def __init__(self, proc, queue=None, ctx=None):
		"""Parse an input stream and pass the commands to the processor
		@proc."""
		if queue:
			self.queue = queue
		else:
			self.queue = Queue.Queue()
		self.result = threads.deferToThread(self._parse)
		self.proc = proc
		self.ctx = ctx() or Context()

	def line(self, line):
		"""Feed a Python-style input line to the parser."""
		self.queue.put(line)

	def readline(self):
		q = self.queue
		if q is None:
			return ""
		from time import sleep
		l = q.get()
		if l is None:
			self.queue = None
			return ""
		return l

	def done(self):
		q = self.queue
		if q is not None:
			q.put(None)

	def _parse(self):
		"""\
			Iterator. It gets fed tokens, assembles them into
			statements, and calls the processor with them.
			"""
		state=0
		last_block = None
		hdl = None
		stack = []
		proc = self.proc

		from token import NUMBER,NAME,DEDENT,INDENT,OP,NEWLINE,ENDMARKER, \
			STRING
		from tokenize import COMMENT,NL

		# States: 0 newline, 1 after first word, 2 OK to extend word
		#         3+4 need newline+indent after sub-level start, 5 extending word
		# TODO: write a nice .dot file for this stuff
		for t,txt,beg,end,line in generate_tokens(self.readline):
			if "logger" in self.ctx: self.ctx.logger(state,t,txt,beg,end,line)
			if t == COMMENT:
				continue
			if state == 0: # begin of statement
				if t == NAME:
					args = [txt]
					state=1
					continue
				elif t == DEDENT:
					proc.done()
					if stack:
						proc = stack.pop()
						continue
					else:
						return
					
				elif t == ENDMARKER:
					proc.done()
					while stack:
						proc = stack.pop()
						proc.done()
					return
				elif t == NL:
					continue
			elif state == 1 or state == 2: # after first word
				if t == NAME:
					args.append(txt)
					state = 2
					continue
				elif t == OP and txt == "*" and state == 1:
					args.append(txt)
					state = 1
					continue
				elif t == NUMBER:
					args.append(eval(txt,{},{}))
					state = 1
					continue
				elif t == STRING:
					args.append(eval(txt,{},{}))
					state = 1
					continue
				elif t == OP and txt == "." and state == 2:
					state = 5
					continue
				elif t == OP and txt == ":":
					p = proc.complex_statement(args)
					stack.append(proc)
					proc = p
					state = 3
					continue
				elif t == NEWLINE:
					proc.simple_statement(args)
					state=0
					continue
			elif state == 3:
				if t == NEWLINE:
					state = 4
					continue
			elif state == 4:
				if t == INDENT:
					state = 0
					continue
			elif state == 5:
				if t == NAME:
					args[-1] += "."+txt
					state = 2
					continue

			raise SyntaxError("Unknown token '%s' (%d, state %d) in %s:%d" % (txt,t,state,fname,beg[0]))


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
	def __init__(self,parent=None, args=(), ctx=None):
		assert isinstance(self.name,tuple)
		self.parent = parent
		self.ctx = ctx or Context()
	
	def __repr__(self):
		return "‹%s %s›" % (self.__class__.__name__,repr(self.name))

	@classmethod
	def matches(self,args):
		"""Check if this statement can process this list of words."""
		if len(args) < len(self.name): return False
		return self.name == tuple(args[0:len(self.name)])

class SimpleStatement(Statement):
	"""\
		Base class for simple statements.
		"""

	def input(self,words):
		raise NotImplementedError("You need to override '%s.input' (called with %s)" % (self.__class__.__name__,repr(words)))

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

	@classmethod
	def matches_complex(self,args):
		return self.matches(args)

	def input_complex(self,args):
		raise NotImplementedError("You need to override '%s.input' (called with %s)" % (self.__class__.__name__,repr(args)))

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

		raise KeyError("Cannot find word",self.name,self.__words,args)
		
	def get_processor(self):
		"""\
			Returns the translator that should process my substatements.
			By default, returns a CollectParentProcessor.
			"""
		return CollectParentProcessor(self)
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
			Register a handler for a token. handler.input() is called
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

	def unregister_statement(self,handler):
		"""\
			Remove this statement.
			"""
		del self.__words[handler.name]


class Help(SimpleStatement):
	name=("help",)
	doc="show doc texts"
	long_doc="""\
The "help" command shows which words are recognized at each level.
"help foo" also shows the sub-commands, i.e. what would be allowed
in place of the "XXX" …

	foo:
		XXX
"""

	def input(self,wl):
		words = self.parent

		wl = wl[1:]
		while wl:
			try:
				wlist = words._get_wordlist()
			except AttributeError:
				break

			n = len(wl)
			while n >= 0:
				try:
					words = wlist[tuple(wl[:n])]
				except KeyError:
					pass
				else:
					wl = wl[n:]
					break
				n = n-1
			if n < 0:
				break

		if wl:
			print >>self.ctx.out,"Not a command:"," ".join(wl)

		try:
			doc = ":\n"+words.long_doc.rstrip("\n")
		except AttributeError:
			doc = " : "+words.doc
		print >>self.ctx.out," ".join(words.name)+doc

		try:
			wlist = words._get_wordlist()
		except AttributeError:
			pass
		else:
			if words is not self.parent:
				print >>self.ctx.out,"Known words:"
			maxlen=0
			for h in words.iterkeys():
				hlen = len(" ".join(h))
				if hlen > maxlen: maxlen = hlen
			def nam(a,b):
				return cmp(a.name,b.name)
			for h in sorted(words.itervalues(),nam):
				hname = " ".join(h.name)
				print >>self.ctx.out,hname+(" "*(maxlen+1-len(hname)))+": "+h.doc

class main_words(ComplexStatement):
	name = ("Main",)
	doc = "word list:"

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
		fn(parent=me, ctx=self.ctx).input(args)

	def complex_statement(self,args):
		me = self.ctx.words
		fn = me.lookup(args)
		fn = fn(parent=me, ctx=self.ctx)
		fn.input_complex(args)
		return fn.processor(parent=fn,ctx=self.ctx(words=fn))
	
	def done(self):
		print >>self.ctx.out,"Exiting"

def _parse(g,input):
	"""Internal code for parse() which reads the input in a separate thread"""
	while True:
		l = input.readline()
		if not l:
			break
		g.line(l)
	g.done()

def parse(input, proc, ctx=None):
	"""\
		Read input (which must be something with a readline() method),
		run through the tokenizer, pass to @cmd's add().
		"""
	if not ctx: ctx=Context
	ctx = ctx(fname="<stdin>")
	g = Parser(proc, ctx=ctx)
	d = threads.deferToThread(_parse,g,input) # read the input
	d.addCallback(lambda _: g.result)         # analyze the result
	return d

class ParserProtocol(LineProtocol,Parser):
	def __init__(self, proc, producer, ctx=None):
		Parser.__init__(proc,ctx)
		LineProtocol.init(self)
		*TODO*

if __name__ == "__main__":
	main_words.register_statement(Help)

	def logger(*x):
		print " ".join((str(d) for d in x))

	import sys
	d = parse(sys.stdin, logger=logger)
	d.addBoth(lambda _: reactor.stop())

	reactor.run()

