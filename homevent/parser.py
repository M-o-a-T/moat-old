# -*- coding: utf-8 -*-

"""\
This code parses input lines.

By itself, it understands nothing whatsoever.

See the homevent.config module and the test/parser.py script
for typical usage.

"""

from zope.interface import implements
from homevent.tokize import tokizer
import Queue
import sys
import os
from twisted.internet import reactor,threads,defer,interfaces
from twisted.python import failure
from twisted.protocols.basic import LineOnlyReceiver,FileSender,_PauseableMixin
from threading import Lock

from homevent.logging import log,TRACE
from homevent.context import Context
from homevent.io import Outputter,conns
from homevent.run import process_failure
from homevent.event import Event
from homevent.statement import global_words
from homevent.twist import deferToLater

PLOG = ("HOMEVENT_LOG_PARSE" in os.environ)

class SimpleReceiver(LineOnlyReceiver,object):
	delimiter = "\n"

	def __init__(self, parser):
		super(SimpleReceiver,self).__init__()
		self.parser = parser

	def lineReceived(self, data):
		if PLOG: print "S LINE",repr(data)
		self.parser.add_line(data)
	
	def write(self, data):
		if PLOG: print "S WRITE",self.transport,repr(data)
		self.dataReceived(data)
	
	def registerProducer(self, producer, streaming):
		if PLOG: print "S START"
		self.parser.registerProducer(producer, streaming)
	
	def unregisterProducer(self):
		if PLOG: print "S STOP"
		self.parser.unregisterProducer()

def buildReceiver(stream,parser):
	"""\
		Convert a simple input stream to a line-based pauseable protocol
		and registers it with the parser.
		"""
	rc = SimpleReceiver(parser)
	fs = FileSender()
	fs.disconnecting = False
	rc.makeConnection(fs)
	r = fs.beginFileTransfer(stream, rc)
	r.addBoth(parser.endConnection)

class ParseReceiver(Outputter):
	"""This is a mixin to feed a parser"""
	implements(interfaces.IHalfCloseableProtocol)
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
		parser.registerProducer(self)
		#parser.startParsing()
	
	def readConnectionLost(self):
		try:
			rl = super(ParseReceiver,self).readConnectionLost
		except AttributeError:
			pass
		else:
			rl()
		if self.parser:
			self.parser.endConnection()
			self.parser = None
		
	def connectionLost(self,reason):
		self.readConnectionLost()
		self.writeConnectionLost()

	def writeConnectionLost(self):
		try:
			rl = super(ParseReceiver,self).writeConnectionLost
		except AttributeError:
			super(ParseReceiver,self).connectionLost("unknown")
		else:
			rl()

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
	if cls is None:
		cls = LineOnlyReceiver
		impl = interfaces.IPushProducer
	else:
		impl = None
	try:
		ctx = k.pop("ctx")
	except KeyError:
		ctx = Context
	if interpreter is None:
		from homevent.interpreter import InteractiveInterpreter
		interpreter = InteractiveInterpreter

	class mixer(ParseReceiver,cls):
		if impl:
			implements(impl)
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
	"""The input parser object. It is a consumer of lines."""
	line = None
	implements(interfaces.IFinishableConsumer)

	def __init__(self, proc, ctx=None):
		"""Parse an input stream and pass the commands to the processor
		@proc."""
		super(Parser,self).__init__()

		self.symbol_queue = Queue.Queue(1)
		self.next_symbol_queue = Queue.Queue(0)
		self.result = defer.Deferred()
		self.ending = False

		self.proc = proc
		self.p_wait = []
		self.p_wait_lock = Lock()
		self.p_queued = None
		self.restart_producer = False

		if ctx is None:
			self.ctx = Context()
		else:
			self.ctx = ctx

		if "filename" not in self.ctx:
			self.ctx.filename="<stdin?>"

		def ex(_):
			if self.line is not None:
				if hasattr(self.line,"loseConnection"):
					self.line.loseConnection()
				elif hasattr(self.line,"stopProducing"):
					self.line.stopProducing()
			return _
		self.result.addBoth(ex)

	def registerProducer(self, producer, streaming=None):
		if PLOG: print >>sys.stderr,"PRODUCE",streaming,producer
		if streaming is None:
			if interfaces.IPushProducer.implementedBy(producer.__class__):
				streaming = True
			elif interfaces.IPullProducer.implementedBy(producer.__class__):
				streaming = False
			elif interfaces.IProducer.implementedBy(producer.__class__):
				raise RuntimeError("Some sort of producer: "+str(producer))
			else:
				if hasattr(producer,"pauseProducing"):
					raise RuntimeError("A PushProducer: "+str(producer.__class__.__mro__))
				elif hasattr(producer,"resumeProducing"):
					raise RuntimeError("A PullProducer: "+str(producer.__class__.__mro__))
				else:
					#raise RuntimeError("Not a producer: "+str(producer.__class__.__mro__))
					buildReceiver(producer,self)
					return
		self.line = producer

		self.streaming = streaming
		self.stream_off = True
	
	def unregisterProducer(self):
		if PLOG: print >>sys.stderr,"PRODUCE UNREG",self.line
		self.line = None
		self.finish()
	
	def finish(self):
		self.endConnection()

	def endConnection(self, res=None):
		"""Called to stop"""
		d = defer.Deferred()
		e = deferToLater(self._endConnection,d,res)
		e.addErrback(process_failure)
		return d

	def _endConnection(self,d,r):
		if self.p_queued:
			if PLOG: print "LINE> STOP"
			q = self.p_queued
			self.p_queued = None
			q.errback(failure.Failure(StopIteration()))

		if not self.ending:
			if PLOG: print "LINE> ENDING"
			self.ending = True
			self.p_wait.append(None)
			self.process_line_buffer()
		if PLOG: print "LINE> END"

		def ex(_):
			d.callback(r)
			self._last_symbol()
			return _
		self.result.addBoth(ex)

	def _last_symbol(self):
		q = self.next_symbol_queue
		if q:
			if PLOG: print >>sys.stderr,"WANT TOKEN last"
			self.next_symbol_queue = None
			q.put(False,block=True)
		if PLOG: print >>sys.stderr,"WANT TOKEN last2"

	def add_line(self, data):
		"""Standard LineReceiver method"""
		if not isinstance(data,unicode):
			data = data.decode("utf-8")
		self.p_wait.append(data)
		self.process_line_buffer()

	def process_line_buffer(self):
		if not self.p_wait_lock.acquire(False):
			return

		if self.p_queued:
			self.resumeProducing()

		while self.p_wait and self.p_queued:
			item = self.p_wait.pop(0)
			if PLOG: print >>sys.stderr,"LINE>",repr(item)
			q = self.p_queued
			self.p_queued = None
			if item is None:
				q.errback(failure.Failure(StopIteration()))
			else:
				q.callback(item)
		if PLOG:
			if self.p_wait:
				print >>sys.stderr,"LINE: input available"
			if self.p_queued:
				print >>sys.stderr,"LINE: wait for input"

		if self.p_wait:
			self.pauseProducing()
		self.p_wait_lock.release()

	def pauseProducing(self):
		if self.line is not None and hasattr(self.line,"pauseProducing") \
				and not self.stream_off and not self.ending:
			if PLOG: print >>sys.stderr,"LINE pause"
			self.line.pauseProducing()
			if self.streaming:
				self.stream_off = True
		elif PLOG:
			if self.line is None:
				print >>sys.stderr,"LINE_PAUSE no line"
			if not hasattr(self.line,"pauseProducing"):
				print >>sys.stderr,"LINE_PAUSE cannot pause"
			if self.stream_off:
				print >>sys.stderr,"LINE_PAUSE already off"
			if self.ending:
				print >>sys.stderr,"LINE_PAUSE ending"

	def stopProducing(self):
		if self.line is not None and hasattr(self.line,"stopProducing") \
				and not self.ending:
			if PLOG: print >>sys.stderr,"LINE stop"
			self.line.stopProducing()
		elif PLOG:
			if self.line is None:
				print >>sys.stderr,"LINE_STOP no line"
			if not hasattr(self.line,"stopProducing"):
				print >>sys.stderr,"LINE_STOP cannot stop"
			if self.ending:
				print >>sys.stderr,"LINE_STOP ending"

	def resumeProducing(self):
		self.process_line_buffer()
		if self.line is not None and hasattr(self.line,"resumeProducing") \
				and self.stream_off and not self.ending:
			if PLOG: print >>sys.stderr,"LINE resume",self.line
			self.line.resumeProducing()
			if self.streaming:
				self.stream_off = False
		elif PLOG:
			if self.line is None:
				print >>sys.stderr,"LINE_RES no line"
			if not hasattr(self.line,"resumeProducing"):
				print >>sys.stderr,"LINE_RES cannot resume"
			if not self.stream_off:
				print >>sys.stderr,"LINE_RES already on"
			if self.ending:
				print >>sys.stderr,"LINE_RES ending"

	def read_a_line(self):
		if PLOG: print >>sys.stderr,"P READ_A_LINE"
		if self.p_queued:
			raise RuntimeError("read_a_line: already waiting")
		q = self.p_queued = defer.Deferred()
		self.process_line_buffer()
		return q

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
		if PLOG: print >>sys.stderr,"P START",protocol

		if protocol is not None:
			protocol.addDropCallback(self.endConnection)
			self.line = protocol
		assert self.line is not None, "no input whatsoever?"


		if "out" not in self.ctx:
			self.ctx.out=sys.stdout

		self.init_state()

		self.p_gen = tokizer(self.read_a_line, self._do_parse)
		def pg_done(_):
			if PLOG:
				print >>sys.stderr,"P DONE",_
			try: self.result.callback(_)
			except defer.AlreadyCalledError: pass
			else: self.endConnection()
		def pg_err(_):
			if PLOG: print >>sys.stderr,"P ERROR",_
			try: self.result.errback(_)
			except defer.AlreadyCalledError: pass
			else: self.endConnection()
		self.p_gen.addCallbacks(pg_done,pg_err)

	def _do_parse(self, t,txt,beg,end,line):
		# States: 0 newline, 1 after first word, 2 OK to extend word
		#         3+4 need newline+indent after sub-level start, 5 extending word
		if PLOG: print >>sys.stderr,"PARSE",t,repr(txt)

		def handle_error(_):
			if _.check(StopIteration):
				_.raiseException()

			if self.p_stack:
				self.proc = self.p_stack[0]

			try:
				if PLOG: print >>sys.stderr,"PERR",self,self.proc
				self.proc.error(self,_)
				if PLOG: print >>sys.stderr,"PERR OK"
			except BaseException,e:
				try:
					if PLOG: print >>sys.stderr,"RESULT error",_
					self.result.errback(_)
				except defer.AlreadyCalledError: pass
				else: self.endConnection()

		res = defer.maybeDeferred(self._parseStep,t,txt,beg,end,line)
		res.addErrback(handle_error)
		return res

	def _parseStep(self, t,txt,beg,end,line):
		from token import NUMBER,NAME,DEDENT,INDENT,OP,NEWLINE,ENDMARKER, \
			STRING
		from tokize import COMMENT,NL

		if "logger" in self.ctx:
			self.ctx.logger("T",self.p_state,t,repr(txt),beg,end,repr(line))
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
				if PLOG:
					print >>sys.stderr,"RUN2"
					print >>sys.stderr,self.proc.complex_statement,self.p_args
				p = defer.maybeDeferred(self.proc.complex_statement,self.p_args)

				def have_p(_):
					self.p_stack.append(self.proc)
					self.proc = _
					self.p_state = 3
				p.addCallback(have_p)
				return p
			elif t == NEWLINE:
				if PLOG:
					print >>sys.stderr,"RUN3"
					print >>sys.stderr,self.proc.simple_statement,self.p_args
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

class _drop(object):
	def __init__(self,g):
		self.g = g
		self.lost = False
		conns.append(self)
	def loseConnection(self):
		self.lost = True
		if PLOG: print >>sys.stderr,"LAST_SYM _drop"
		self.g._last_symbol()
	def drop(self,_):
		if PLOG: print >>sys.stderr,"LAST_SYM drop"
		conns.remove(self)
		self.loseConnection()
		return _

def parse(input, proc=None, ctx=None):
	"""\
		Read non-blocking input, run through the tokenizer, pass to the
		parser.
		"""
	if not ctx: ctx=Context
	if ctx is Context or "fname" not in ctx:
		ctx = ctx(fname="<stdin>")
	if proc is None: proc = global_words(ctx)

	g = Parser(proc, ctx=ctx)
	x = _drop(g)
	g.result.addBoth(x.drop)
	g.registerProducer(input)
	g.startParsing()
	return g.result

def read_config(ctx,name, interpreter=None):
	"""Read a configuration file."""
	if interpreter is None:
		from homevent.interpreter import Interpreter
		interpreter = Interpreter
	input = open(name,"rU")
	ctx = ctx()
	return parse(input, Interpreter(ctx),ctx)


