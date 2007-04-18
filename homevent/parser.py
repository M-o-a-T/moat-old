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

class Parser(object):
	def __init__(self, words=None, out=None, logger=None, level=0, queue=None):
		if words is None:
			words = main_words(None, out=out)
		self.words = words
		self.out=out
		self.logger=logger
		self.level=level
		if queue:
			self.queue = queue
		else:
			self.queue = Queue.Queue()
		self.result = threads.deferToThread(self._parse)

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
			statements, and calls the code in 'words' with them.
			"""
		if self.level:
			state=3
		else:
			state=0
		last_block = None
		hdl = None
		stack = []
		level = self.level
		words = self.words

		from token import NUMBER,NAME,DEDENT,INDENT,OP,NEWLINE,ENDMARKER, \
			STRING
		from tokenize import COMMENT,NL

		# States: 0 newline, 1 after first word, 2 OK to extend word
		#         3+4 need newline+indent after sub-level start, 5 extending word
		# TODO: write a nice .dot file for this stuff
		for t,txt,beg,end,line in generate_tokens(self.readline):
			if self.logger: self.logger(state,t,txt,beg,end,line)
			if t == COMMENT:
				continue
			if state == 0: # begin of statement
				if t == NAME:
					args = [txt]
					state=1
					continue
				elif t == DEDENT and level>0:
					words.end_block()
					if stack:
						words = stack.pop()
						continue
					else:
						return
					
				elif t == ENDMARKER:
					stack.append(words)
					while stack:
						words = stack.pop()
						if hasattr(words,"end_block"):
							words.end_block()
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
					stack.append(words)
					words,w = words.lookup_block(*args)
					words.input_block(*w)
					level += 1
					state = 3
					continue
				elif t == NEWLINE:
					fn,w = words.lookup_block(*args)
					fn.input(*w)
					# reactor.callFromThread(hdl.input,*args)
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

			raise SyntaxError("Unknown token '%s' (%d, state %d) in line %d" % (txt,t,state,beg[0]))

def _parse(g,input):
	while True:
		l = input.readline()
		if not l:
			break
		g.line(l)
	g.done()

def parse(input, *a,**k):
	"""\
		Read input (which must be something with a readline() method)
		and run through the tokenizer.
		"""
	g = Parser(*a,**k)
	d = threads.deferToThread(_parse,g,input)
	d.addCallback(lambda _: g.result)
	return d


class Statement(object):
	"""\
		Base class for handling short statements. Doesn't really do anything.
		"""
	name="(unassigned!)"
	doc="(unassigned short help text!)"
#	long_doc="""\
#This statement has a help text that has not been overridden.
#Programmer error!
#"""
	def __repr__(self):
		return "<Statement <%s>>" % (self.name,)

	def __init__(self,parent, out=None):
		self.parent = parent
		self.out = out

	def input(self,*words):
		raise NotImplementedError("You need to override '%s.input' (called with %s)" % (self.name,repr(words)))
	
	def input_block(self,*words):
		raise NotImplementedError("'%s' is not a StatementBlock (called with %s)" % (self.name,repr(words)))
	

class StatementBlockHelper(object):
	def __init__(self,obj,words):
		self.obj = obj

	def __getitem__(self,w):
		return self.obj._lookup_word[w]

class StatementBlock(Statement):
	"""\
		Base class for handling compound statements.
		"""
	__words = None

	def __repr__(self):
		return "<StatementBlock <%s> %d>" % (self.name,len(self.__words))

	def input_block(self,*w):
		"""\
			Override this if you want to replace the default lookup
			code for sub-statements.
			"""
		if self.__words is None:
			raise NotImplementedError("No words in "+self.__class__.__name__)
		pass
	
	def lookup_block(self,*w):
		"""\
			Standard method which looks up a sub-object, and the words to
			call it with.
			"""
		try:
			res = self.__words[w[0]]
		except KeyError:
			res = self.__words["*"]
			return res(self),w
		else:
			return res(self),w[1:]

		return ( self.__words[w[0]](self), w[1:] )

	def end_block(self):
		"""\
			Override this if you want a notification that your sub-statement
			is complete.
			"""
		pass
	
	@classmethod
	def _get_wordlist(self):
		"""Called by Help to get the list of words."""
		return self.__words
	@classmethod
	def _lookup_word(self,w):
		"""Called by StatementBlockHelper to get the handler for a word."""
		return self.__words[w]
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


class Help(Statement):
	name="help"
	doc="show doc texts"
	def __init__(self,parent,out=None):
		super(Help,self).__init__(parent)
		if out is None:
			out = parent.out
			if out is None:
				from sys import stdout
				out = stdout
		self.out=out

	def input(self,*wl):
		words = self.parent

		for w in wl:
			try:
				wlist = words._get_wordlist()
			except AttributeError:
				wlist = None

			if wlist is None:
				self.out("No more arguments: "+str(w))
				break
			try:
				words = wlist[w]
			except KeyError:
				self.out("Unknown argument: "+str(w))
				break

		if words:
			try:
				doc = ":\n"+words.long_doc
			except AttributeError:
				doc = " "+words.doc
			self.out(words.name+doc)

			try:
				wlist = words._get_wordlist()
			except AttributeError:
				pass
			else:
				if wl:
					self.out("Known words:")
				maxlen=0
				for h in words.iterkeys():
					if len(h) > maxlen: maxlen = len(h)
				for h in words.itervalues():
					self.out(h.name+(" "*(maxlen+1-len(h.name)))+h.doc)

class main_words(StatementBlock):
	name = "Main"
	doc = "word list:"

if __name__ == "__main__":
	main_words.register_statement(Help)

	def logger(*x):
		print " ".join((str(d) for d in x))

	import sys
	d = parse(sys.stdin, logger=logger)
	d.addBoth(lambda _: reactor.stop())

	reactor.run()

