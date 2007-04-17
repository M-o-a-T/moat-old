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

main_words = {}

def register_statement(handler, words=main_words):
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
	if handler.name in words:
		raise ValueError("A handler for '%s' is already registered." % (handler.name,))
	words[handler.name] = handler

def unregister_statement(handler, words=main_words):
	"""\
		Remove this statement.
		"""
	del words[handler.name]

class Parser(object):
	def __init__(self, words=main_words, logger=None, level=0, queue=None):
		self.words = words
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
					try:
						hdl = words[txt]
					except KeyError:
						try:
							hdl = words["*"]
						except KeyError:
							raise NameError("'%s': not found; line %d" % (txt,beg[0]))
						else:
							args = [txt]
					else:
						args = []
					state=1
					continue
				elif t == DEDENT and level>0:
					if hasattr(words,"end_block"):
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
					words = (hdl.input_block(*args))
					level += 1
					state = 3
					continue
				elif t == NEWLINE:
					hdl.input(*args)
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

def _parse(g,input, *a,**k):
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
	d = threads.deferToThread(_parse,g,input,*a,**k)
	d.addCallback(lambda _: g.result)
	return d


class Statement(object):
	"""\
		Interface class for short statements. Doesn't really do anything.
		"""
	name="(unassigned!)"
	doc="(unassigned short help text!)"
#	long_doc="""\
#This statement has a help text that has not been overridden.
#Programmer error!
#"""
	def input(self,*words):
		raise NotImplementedError("You need to override '%s.input' (called with %s)" % (self.name,repr(words)))
	
	def input_block(self,*words):
		raise NotImplementedError("You need to override '%s.input' (called with %s)" % (self.name,repr(words)))
	

	def __getitem__(self,w):
		return self.words[w]

class StatementBlockHelper(object):
	def __init__(self,obj,words):
		self.obj = obj
		self.words = words

	def __getitem__(self,w):
		return self.words[w](*self.obj)

class StatementBlock(Statement):
	"""\
		Base class for objects returned by compound statements.
		"""

	words = None

	def end_block(self):
		"""\
			Override this if you want a notification that your statement
			has processed its last line.
			"""
		pass
	
	def input_block(self,*w):
		"""\
			"""
		if self.words is None:
			raise NotImplementedError("No words in "+self.__class__.__name__)
		obj = self.input_obj(*w)
		return StatementBlockHelper(obj,self.words)

	def input_obj(self,*w):
		"""\
			Override this method to return an initial argument list for
			the command handlers that process this sub-block.

			Thus, if this is the handler for "foo", and this input is
			processed:
				foo bar:
					baz quux
			this code should return something related to "bar".
			The class registered for "baz" will get inited with it,
			and then gets called with .input("quux").
			"""
		raise NotImplementedError("You need to override '%s.input_obj' (called with %s)" % (self.name,repr(words)))

	@classmethod
	def register_statement(self,handler):
		"""\
			Register a handler for sub-statements.
			The handler registered here will be called with the word
			list to initialize a Statement or StatementBlock object.
			"""
		if self.words is None:
			self.words = {}
		register_statement(handler,self.words)

	@classmethod
	def unregister_statement(self,handler):
		unregister_statement(handler,self.words)
	

class Help(Statement):
	name="help"
	doc="show doc texts"
	def __init__(self,out=None):
		if out is None:
			from sys import stdout
			out = stdout
		self.out=out

	def input(self,*wl):
		words = main_words
		last = None

		for w in wl:
			if words is None:
				print >>self.out,"No more arguments:",w
				break
			try:
				last = words[w]
			except KeyError:
				print >>self.out,"Unknown argument:",w
				break
			else:
				try:
					words = last.words
				except AttributeError:
					words = None

		if last:
			try:
				doc = ":\n"+last.long_doc
			except AttributeError:
				doc = " "+last.doc
			print >>self.out,last.name+doc

		if words:
			if last:
				print >>self.out,"Known words:"
			else:
				print >>self.out,"Known sub-words:"
			maxlen=0
			for h in words.iterkeys():
				if len(h) > maxlen: maxlen = len(h)
			for h in words.itervalues():
				print >>self.out, h.name+(" "*(maxlen+1-len(h.name)))+h.doc

if __name__ == "__main__":
	register_statement(Help())

	def logger(*x):
		print " ".join((str(d) for d in x))

	import sys
	d = parse(sys.stdin, logger=logger)
	d.addBoth(lambda _: reactor.stop())

	reactor.run()

