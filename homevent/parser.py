#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
This code reads a config file.

Currently, it understands:

include NAME
		- read that file too

load NAME
		- load the module/package homevent.NAME

unload NAME
		- ... and remove it again.

config NAME:
	foo bar baz
		- pass these lines to this module's config() code
		- see there for further documentation

Modules can register more words. Of particular interest are the
switchboard and timer modules.

"""

from tokenize import generate_tokens

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

def parse(input, *a,**k):
	"""\
		Read input (which must be something with a readline() method)
		and run through the tokenizer.
		"""
	return parse_tokens(generate_tokens(input.readline), *a,**k)

def parse_tokens(stream, level=0, logger=None, words=main_words):
	"""\
		Read input stream, which must be an iterable(!) returning tokens,
		as returned by tokenize.generate_tokens().
		Call the code in 'words'.
		"""
	words=words
	if level:
		state=3
	else:
		state=0
	last_block = None
	hdl = None

	from token import NAME,DEDENT,INDENT,OP,NEWLINE,ENDMARKER
	from tokenize import COMMENT,NL

	for t,txt,beg,end,line in stream:
		if logger: logger(state,t,txt,beg,end,line)
		if t == COMMENT:
			continue
		if state == 0: # begin of statement
			if t == NAME:
				try:
					hdl = words[txt]
				except KeyError:
					raise NameError("'%s': not found; line %d" % (txt,beg[0]))
				state=1
				args = []
				continue
			elif t == DEDENT and level>0:
				if hasattr(words,"end_block"):
					words.end_block()
				return
			elif t == ENDMARKER:
				return
			elif t == NL:
				continue
		elif state == 1: # after first word
			if t == NAME:
				args.append(txt)
				continue
			elif t == OP and txt == ":":
				parse_tokens(stream, words=hdl.input_block(*args), level=level+1, logger=logger)
				state=0
				continue
			elif t == NEWLINE:
				hdl.input(*args)
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

		raise SyntaxError("Unknown token '%s' (%d, state %d) in line %d" % (txt,t,state,beg[0]))

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
	parse(sys.stdin, logger=logger)

