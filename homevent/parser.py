#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
This code parses input lines.

By itself, it understands nothing whatsoever.

See the homevent.config module and the test/parser.py script
for typical usage.

"""

from homevent.tokize import generate_tokens
import Queue
import sys
from twisted.internet import reactor,threads,defer
from twisted.python import failure
from twisted.protocols.basic import LineReceiver
from threading import Lock

from homevent.context import Context
from homevent.io import Outputter
from homevent.run import process_failure
from homevent.event import Event
from homevent.statement import global_words


class ParseReceiver(Outputter):
	"""This is a mixin to feed a parser"""
	delimiter = '\n'

	def __init__(self, parser=None, *a,**k):
		super(ParseReceiver,self).__init__(*a,**k)
		if parser is None:
			from homevent.interpreter import InteractiveInterpreter

			def reporter(err):
				print >>sys.stderr,"Error:",err
			c=Context()
			#c.logger=parse_logger
			i = InteractiveInterpreter(ctx=c)
			p = Parser(i, StdIO, ctx=c)
			r = p.result
			r.addErrback(reporter)
			parser = p
		self.parser = parser
	
	def connectionLost(self,reason):
		super(ParseReceiver,self).connectionLost(reason)
		self.parser.endConnection()
		self.parser = None

	def lineReceived(self, data):
		self.parser.add_line(data)
	
	def makeConnection(self,transport):
		assert not hasattr(self,"goforit"),"Go for it"
		self.goforit=True
		assert self.parser is not None, "Need to set the parser"
		if "out" not in self.parser.ctx:
			self.parser.ctx.out = transport

		super(ParseReceiver,self).makeConnection(transport)

	def connectionMade(self):
		super(ParseReceiver,self).connectionMade()
		self.parser.startParsing(self)
		self.parser.proc.prompt()

def parser_builder(cls=None,interpreter=None,*a,**k):
	"""\
		Return something that builds a receiver class when called with
		no arguments
		"""
	if cls is None: cls = LineReceiver
	try:
		ctx = k.pop("ctx")
	except KeyError:
		ctx = Context
	if interpreter is None:
		from homevent.interpreter import InteractiveInterpreter
		interpreter = InteractiveInterpreter

	class mixer(ParseReceiver,cls):
		pass
	def gen_builder(*x,**y):
		c = ctx()
		k["ctx"] = c
		i = interpreter(ctx=c)
		p = Parser(i, *a,**k)
		m = mixer(p, *x,**y)
		return m
	return gen_builder


class Parser(object):
	"""The input parser object. It serves as a LineReceiver and a 
	   normal (but non-throttle-able) producer."""
	delimiter="\n"

	def __init__(self, proc, ctx=None, delimiter=None):
		"""Parse an input stream and pass the commands to the processor
		@proc."""
		super(Parser,self).__init__()

		self.line_queue = Queue.Queue(10)
		self.symbol_queue = Queue.Queue()
		self.result = defer.Deferred()
		self.more_parsing = None
		self.ending = False

		self.proc = proc
		self.p_wait = []
		self.p_wait_lock = Lock()
		self.restart_producer = False

		if ctx is None:
			self.ctx = Context()
		else:
			self.ctx = ctx

		if "filename" not in self.ctx:
			self.ctx.filename="<stdin?>"
		if delimiter:
			self.delimiter=delimiter

		def ex(_):
			if self.line is not None:
				self.line.loseConnection()
			return _
		self.result.addBoth(ex)

	def endConnection(self, res=None):
		"""Called to stop"""
		d = defer.Deferred()
		#reactor.callLater(0,self._endConnection,d,res)
		self._endConnection(d,res)
		return d

	def _endConnection(self,d,r):
		def ex(_):
			d.callback(r)
			return _
		if self.ending:
			self.result.addBoth(ex)
			return

		self.ending = True
		q = self.line_queue
		if q is not None:
			try:
				q.put(None, block=(self.line is None))
			except Queue.Full:
				reactor.callInThread(q.put,None,block=True)
		self.result.addBoth(ex)

	def add_line(self, data):
		"""Standard LineReceiver method"""
		self.p_wait.append(data)
		self.process_line_buffer()

	def process_line_buffer(self):
		if not self.p_wait_lock.acquire(False):
			return

		try:
			while self.p_wait:
				item = self.p_wait.pop(0)
				q = self.line_queue
				if q: q.put(item, block=(self.line is None))
		except Queue.Full:
			self.p_wait.insert(0,item)
			self.pauseProducing()

		self.p_wait_lock.release()

	def pauseProducing(self):
		if self.line is not None and hasattr(self.line,"pauseProducing"):
			self.line.pauseProducing()

	def stopProducing(self):
		if self.line is not None and hasattr(self.line,"stopProducing"):
			self.line.stopProducing()

	def resumeProducing(self):
		self.process_line_buffer()
		if self.line is not None and hasattr(self.line,"resumeProducing"):
			self.line.resumeProducing()

	def readline(self):
		"""Queued ReadLine, to be called from the _sym_parse thread ONLY"""
		q = self.line_queue
		if q is None:
			return ""
		try:
			l = q.get(block=False)
		except Queue.Empty:
			reactor.callFromThread(self.resumeProducing)
			l = q.get(block=True)
		if l is None:
			self.line_queue = None
			return ""
		return l+"\n"

	def init_state(self):
		self.p_state=0
		self.p_pop_after=False
		self.p_stack = []
		self.p_args = []

	def startParsing(self, protocol=None):
		"""\
			Iterator. It gets fed tokens, assembles them into
			statements, and calls the processor with them.
			"""
		if protocol is not None:
			protocol.addDropCallback(self.endConnection)
		self.line = protocol

		if "out" not in self.ctx:
			self.ctx.out=sys.stdout

		self.init_state()
		self.p_gen = generate_tokens(self.readline)
		reactor.callInThread(self._sym_parse)
		self._do_parse()

	def _sym_parse(self):
		"""Thread transferring input lines to symbols."""
		from token import ENDMARKER

		while True:
			t = self.p_gen.next()
			try:
				self.symbol_queue.put(t, block=False)
			except Queue.Full:
				reactor.callFromThread(self.pauseProducing)
				self.symbol_queue.put(t, block=True)
				reactor.callFromThread(self.resumeProducing)
			q = self.more_parsing
			if q is not None:
				self.more_parsing = None
				def cb(q):
					try: q.callback(None)
					except defer.AlreadyCalledError: pass
				reactor.callFromThread(cb,q)
			if t[0] == ENDMARKER:
				return

	def _do_parse(self):
		# States: 0 newline, 1 after first word, 2 OK to extend word
		#         3+4 need newline+indent after sub-level start, 5 extending word
		# TODO: write a nice .dot file for this stuff

		if self.more_parsing is not None:
			return
		while True:
			try:
				t,txt,beg,end,line = self.symbol_queue.get(block=False)
			except Queue.Empty:
				# possible race condition: new 
				self.more_parsing = d = defer.Deferred()
				if not self.symbol_queue.empty():
					try: d.callback(None)
					except defer.AlreadyCalledError: pass
				d.addCallback(lambda _: self._do_parse())
				return

			def handle_error(_):
				if _.check(StopIteration):
					try: self.result.callback(None)
					except defer.AlreadyCalledError: pass
					return

				if self.p_stack:
					self.proc = self.p_stack[0]

				try:
					self.proc.error(self,_)
				except BaseException,e:
					if not isinstance(e,AttributeError):
						from traceback import print_exc
						print_exc()
					try: self.result.errback(_)
					except defer.AlreadyCalledError: pass

			res = defer.maybeDeferred(self._parseStep,t,txt,beg,end,line)
			res.addCallbacks(lambda _: self._do_parse(), handle_error)
			return res

	def _parseStep(self, t,txt,beg,end,line):
		from token import NUMBER,NAME,DEDENT,INDENT,OP,NEWLINE,ENDMARKER, \
			STRING
		from tokize import COMMENT,NL

		if "logger" in self.ctx: self.ctx.logger("T",self.p_state,t,txt,beg,end,line)
		if t == COMMENT:
			return
		if self.p_state == 0: # begin of statement
			if t == NAME:
				self.p_args = [txt]
				self.p_state=1
				return
			elif t == DEDENT:
				r = self.proc.done()
				if self.p_stack:
					self.proc = self.p_stack.pop()
					return r
				else:
					raise StopIteration
			elif t == ENDMARKER:
				self.proc.done()
				while self.p_stack:
					self.proc = self.p_stack.pop()
					self.proc.done()
				raise StopIteration
			elif t in(NL,NEWLINE):
				return
			elif t == OP and txt == ".":
				return # "I am done"
		elif self.p_state in (1,2): # after first word
			if t == NAME:
				self.p_args.append(txt)
				self.p_state = 2
				return
			elif t == OP and txt in ("*","+","-"):
				self.p_args.append(txt)
				self.p_state = 1
				return
			elif t == NUMBER:
				self.p_args.append(eval(txt,{},{}))
				self.p_state = 1
				return
			elif t == STRING:
				self.p_args.append(eval(txt,{},{}))
				self.p_state = 1
				return
			elif t == OP and txt[0] in ("$","*"):
				self.p_args.append(txt)
				self.p_state = 1
				return
			elif t == OP and txt == "." and self.p_state == 2:
				self.p_state = 5
				return
			elif t == OP and txt == ":":
				p = defer.maybeDeferred(self.proc.complex_statement,self.p_args)

				def have_p(_):
					self.p_stack.append(self.proc)
					self.proc = _
					self.p_state = 3
				p.addCallback(have_p)
				return p
			elif t == NEWLINE:
				r = defer.maybeDeferred(self.proc.simple_statement,self.p_args)
					
				if self.p_pop_after:
					r.addCallback(lambda _,p: p.done(), self.proc)
					self.proc = self.p_stack.pop()
					self.p_pop_after=False
				self.p_state=0
				return r
		elif self.p_state == 3:
			if t == NEWLINE:
				self.p_state = 4
				return
			elif t == NAME:
				self.p_args = [txt]
				self.p_state = 1
				self.p_pop_after = True
				return
			else:
				self.proc = self.p_stack.pop()
		elif self.p_state == 4:
			if t == INDENT:
				self.p_state = 0
				return
			elif t == NEWLINE:
				# ignore
				return
			else:
				self.proc = self.p_stack.pop()
		elif self.p_state == 5:
			if t == NAME:
				self.p_args[-1] += "."+txt
				self.p_state = 2
				return

		if self.p_pop_after:
			self.proc = self.p_stack.pop()
			self.p_pop_after = False

		raise SyntaxError("Unknown token %s (%d, state %d) in %s:%d" % (repr(txt),t,self.p_state,self.ctx.filename,beg[0]))


def _parse(g,input):
	"""Internal code for parse() which reads the input in a separate thread"""
	g.startParsing()
	while True:
		l = input.readline()
		if not l:
			break
		g.add_line(l)
	reactor.callFromThread(g.endConnection)

def parse(input, proc=None, ctx=None):
	"""\
		Read input (which must be something with a readline() method),
		run through the tokenizer, pass to @cmd's add().
		"""
	if not ctx: ctx=Context
	ctx = ctx(fname="<stdin>")
	if proc is None: proc = global_words(ctx)
	g = Parser(proc, ctx=ctx)
	d = threads.deferToThread(_parse,g,input) # read the input
	d.addCallback(lambda _: g.result)         # analyze the result
	return d

def read_config(ctx,name, interpreter=None):
	"""Read a configuration file."""
	if interpreter is None:
		from homevent.interpreter import Interpreter
		interpreter = Interpreter
	input = open(name,"rU")
	ctx = ctx()
	return parse(input, Interpreter(ctx),ctx)


