#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
This code parses input lines.

By itself, it understands nothing whatsoever.

See the homevent.config module and the test/parser.py script
for typical usage.

"""

from tokenize import generate_tokens
import Queue
from twisted.internet import reactor,threads,defer
from twisted.python import failure
from twisted.protocols.basic import LineReceiver
from threading import Lock

from homevent.context import Context
from homevent.io import Outputter
from homevent.run import process_failure
from homevent.event import Event
from homevent.statement import global_words


# We need to hack tokenize
import tokenize as t
import re
t.Operator = re.sub(r"\(",r"(\$[0-9]+|[$*]([a-z][a-z0-9]*)?|",t.Operator,count=1)
t.Funny = t.group(t.Operator, t.Bracket, t.Special)
t.PlainToken = t.group(t.Number, t.Funny, t.String, t.Name)
t.Token = t.Ignore + t.PlainToken
t.tokenprog = re.compile(t.Token)
t.PseudoToken = t.Whitespace + t.group(t.PseudoExtras, t.Number, t.Funny, t.ContStr, t.Name)
t.pseudoprog = re.compile(t.PseudoToken)

del t
del re


class Parser(Outputter):
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

		if ctx is None:
			self.ctx = Context()
			self.ctx.out=self
		else:
			if "out" not in ctx:
				ctx.out=self
			self.ctx = ctx()

		if "filename" not in self.ctx:
			self.ctx.filename="<stdin?>"
		if delimiter:
			self.delimiter=delimiter
		self.proc = proc
		self.p_wait = []
		self.p_wait_lock = Lock()
		self.restart_producer = False

		def ex(_):
			self.loseConnection()
			return _
		self.result.addBoth(ex)
		self.addDropCallback(self.endConnection)

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
				q.put(None, block=(self.transport is None))
			except Queue.Full:
				reactor.callInThread(q.put,None,block=True)
		self.result.addBoth(ex)
		if self.transport:
			self.transport.loseConnection()

	def connectionLost(self,reason):
		super(Parser,self).connectionLost(reason)
		self.endConnection()

	def run(self, producer, *a,**k):
		"""Parse this producer's stream."""
		s = producer(self,*a,**k)
		self.proc.prompt()
		self.startParsing()
		return self.result

	def lineReceived(self, data):
		"""Standard LineReceiver method"""
		if data is not None:
			self.p_wait.append(data)

		if not self.p_wait_lock.acquire(False):
			return

		try:
			while self.p_wait:
				item = self.p_wait.pop(0)
				q = self.line_queue
				if q: q.put(item, block=(self.transport is None))
		except Queue.Full:
			self.p_wait.insert(0,item)
			self._pauseProducing()

		self.p_wait_lock.release()

	def _pauseProducing(self):
		if self.transport:
			self.pauseProducing()

	def _resumeProducing(self):
		self.lineReceived(None)
		if self.transport:
			self.resumeProducing()

	def readline(self):
		"""Queued ReadLine, to be called from the _sym_parse thread ONLY"""
		q = self.line_queue
		if q is None:
			return ""
		try:
			l = q.get(block=False)
		except Queue.Empty:
			reactor.callFromThread(self._resumeProducing)
			l = q.get(block=True)
		if l is None:
			self.line_queue = None
			return ""
		return l+"\n"

	def startParsing(self):
		self._parse() # goes to a different thread
		if not self.transport:
			self.connectionMade()

	def init_state(self):
		self.p_state=0
		self.p_pop_after=False
		self.p_stack = []
		self.p_args = []

	def _parse(self):
		"""\
			Iterator. It gets fed tokens, assembles them into
			statements, and calls the processor with them.
			"""
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
				reactor.callFromThread(self._pauseProducing)
				self.symbol_queue.put(t, block=True)
				reactor.callFromThread(self._resumeProducing)
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
		from tokenize import COMMENT,NL

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
		g.lineReceived(l)
	reactor.callFromThread(g.endConnection)
	g.loseConnection()

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


