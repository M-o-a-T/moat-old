# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2008, Matthias Urlichs <matthias@urlichs.de>
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
This code implements (a subset of) the WAGO server protocol.

"""

import os
import re

from homevent.module import Module
from homevent.base import Name,SName, singleName
from homevent.logging import log,log_exc,DEBUG,TRACE,INFO,WARN
from homevent.statement import AttributedStatement, Statement, main_words
from homevent.check import Check,register_condition,unregister_condition
from homevent.monitor import Monitor,MonitorHandler, MonitorAgain
from homevent.net import NetConnect,LineReceiver,NetActiveConnector,NetRetry
from homevent.twist import reraise,callLater,fix_exception
from homevent.run import simple_event
from homevent.context import Context
from homevent.times import humandelta,now,unixdelta
from homevent.msg import MsgQueue,MsgFactory,MsgBase, MINE,NOT_MINE, RECV_AGAIN,SEND_AGAIN,\
	MsgReceiver, MsgClosed, MSG_ERROR,PRIO_URGENT,PRIO_CONNECT
from homevent.collect import Collection
from homevent.in_out import register_input,register_output, unregister_input,unregister_output,\
	Input,Output,BoolIO

from gevent.event import AsyncResult

class WAGOchannels(Collection):
	name = "wago conn"
WAGOchannels = WAGOchannels()

class WAGOserver(Collection):
	name = "wago server"
WAGOserver = WAGOserver()
WAGOserver.does("del")

class MT_MULTILINE(singleName): pass # =foo bar .
class MT_OTHER(singleName): pass # anything else
class MT_INFO(singleName): pass # *
class MT_ERROR(singleName): pass # ?
class MT_ACK(singleName): pass # +
class MT_NAK(singleName): pass # -
class MT_IND(singleName): pass # !num
class MT_IND_ACK(singleName): pass # !+num
class MT_IND_NAK(singleName): pass # !-num


class WAGObadResult(RuntimeError):
	pass

class WAGOerror(RuntimeError):
	pass

class DroppedMonitor(RuntimeError):
	"""After reconnecting, a monitor is gone"""
	def __init__(self,mid):
		self.mid = mid
	def __str__(self):
		return "DroppedMonitor:%d" % (self.mid,)
	def __repr__(self):
		return "DroppedMonitor(%d)" % (self.mid,)

class WAGOassembler(LineReceiver):
	buf = None
	def lineReceived(self, line):
		log("wago",TRACE,"recv",repr(line))
		msgid = 0
		off = 0
		mt = MT_OTHER

		if self.buf is not None:
			if line == ".":
				buf,self.buf = self.buf,None
				self.msgReceived(type=MT_MULTILINE, msg=buf)
			else:
				self.buf.append(line)
			return
		elif line == "":
			self.msgReceived(type=MT_OTHER, msg=line)
		elif line[0] == "=":
			self.buf = [line[1:]]
			return
		elif line[0] == "?":
			self.msgReceived(type=MT_ERROR, msg=line[1:].strip())
			return
		elif line[0] == "*":
			self.msgReceived(type=MT_INFO, msg=line[1:].strip())
			return
		elif line[0] == "+":
			self.msgReceived(type=MT_ACK, msg=line[1:].strip())
			return
		elif line[0] == "-":
			self.msgReceived(type=MT_NAK, msg=line[1:].strip())
			return
		elif line[0] == "!":
			if line[1] == "+":
				mt = MT_IND_ACK
				off = 2
			elif line[1] == "-":
				mt = MT_IND_NAK
				off = 2
			else:
				mt = MT_IND
				off = 1
		while off < len(line) and line[off].isdigit():
			msgid = 10*msgid+int(line[off])
			off += 1
		if msgid > 0:
			self.msgReceived(type=mt, msgid=msgid, msg=line[off:].strip())
		else:
			self.msgReceived(type=mt, msg=line.strip())
	

class WAGOchannel(WAGOassembler, NetActiveConnector):
	"""A receiver for the protocol used by the wago adapter."""
	storage = WAGOchannels
	typ = "wago"

	def handshake(self, external=False):
		pass
		# we do not do anything, except to read a prompt

	def down_event(self, external=False):
		simple_event(Context(),"wago","disconnect",*self.name)

	def up_event(self, external=False):
		simple_event(Context(),"wago","connect",*self.name)

	def not_up_event(self, external=False):
		simple_event(Context(),"wago","error",*self.name)


class WAGOinitMsg(MsgReceiver):
	blocking = True
	start_timer = None
	prio = PRIO_CONNECT
	def __init__(self,queue):
		super(WAGOinitMsg,self).__init__()

		self.queue = queue
		self.start_timer = callLater(True, 0.2 if "HOMEVENT_TEST" in os.environ else 2, self.start_timed_out)

	def start_timed_out(self):
		self.start_timer = None
		if self.queue.channel is not None and self.queue.q is not None:
			m = MsgClosed()
			self.queue.q.put(m, block=False)

	def recv(self,msg):
		if self.blocking is False:
			return NOT_MINE
		if self.start_timer is not None:
			self.start_timer.cancel()
			self.start_timer = None
		if msg.type is MT_INFO:
			self.blocking = False
			self.queue.channel.up_event(False)
			return MINE
		return MSG_ERROR("Initial message:"+repr(msg))

	def done(self):
		self.blocking = False
		if self.start_timer is not None:
			self.start_timer.cancel()
			self.start_timer = None


_num = re.compile("[0-9]+")

class WAGOmonitorsMsg(MsgBase):
	blocking = True
	prio = PRIO_URGENT
	data = None

	def __init__(self,queue):
		self.queue = queue
		self.data = {}
		super(WAGOmonitorsMsg,self).__init__()

	def send(self,conn):
		conn.write(self.msg)
		return RECV_AGAIN

	@property
	def msg(self):
		return "m"

	def list(self):
		for r in super(WAGOmonitorsMsg,self).list():
			yield r
		for a,b in self.data.iteritems():
			yield "found",(a,b)

	def retry(self):
		log("wago",TRACE,"Queue WAGOmonitorsMsg")
		super(WAGOmonitorsMsg,self).retry()
		return None

	def recv(self,msg):
		if msg.type is MT_MULTILINE:
			for x in msg.msg:
				if x == "":
					continue
				m = _num.match(x)
				if m is None:
					continue
				mon = int(m.group(0))
				self.data[mon]=x[m.end():]
				recvs,self.queue.receivers = self.queue.receivers,[]
				for r in recvs:
					mid = getattr(r,"msgid",None)
					if mid is None or mid in self.data:
						log("wago",TRACE,"found monitor",r)
						self.queue.receivers.append(r)
					else:
						try:
							raise DroppedMonitor(mid)
						except DroppedMonitor as ex:
							fix_exception(ex)
							res = r.error(ex)
							if res is SEND_AGAIN:
								log("wago",TRACE,"retry monitor",r)
								self.queue.enqueue(r)
							else:
								log("wago",TRACE,"drop monitor",r)
								assert res is None or res is False, "%s.error returned %s"%(repr(r),repr(res))

			return MINE
		if msg.type is MT_NAK or msg.type is MT_ERROR:
			simple_event(Context(),"wago","monitor","error",msg.msg)
			return MINE
		return NOT_MINE

	def done(self):
		for a,b in self.data.iteritems():
			log("wago",TRACE,"found monitor",a,b)
		pass

	

class WAGOkeepaliveMsg(MsgBase):
	blocking = False
	ping_timer = None
	last_recv = None
	msgid = None

	def __init__(self,queue, tm,maxtm):
		self.queue = queue
		if maxtm is None:
			maxtm = 2*tm
		else:
			maxtm += tm

		self.ping_timeout = tm
		self.max_ping_timeout = maxtm
		super(WAGOkeepaliveMsg,self).__init__()

	def send(self,conn):
		conn.write(self.msg)
		self.ping_start()
		return RECV_AGAIN

	@property
	def msg(self):
		return "Da"+str(self.ping_timeout)

	def list(self):
		for r in super(WAGOkeepaliveMsg,self).list():
			yield r
		yield "last",self.last_recv
		yield "id",self.msgid

	def retry(self):
		"""Do not redo this - setup anew."""
		super(WAGOkeepaliveMsg,self).retry()
		self.msgid = None
		return SEND_AGAIN

	def ping_timed_out(self):
		self.ping_timer = None
		if self.queue.channel is not None and self.queue.q is not None:
			m = MsgClosed()
			self.queue.q.put(m, block=False)

	def ping_start(self):
		if self.ping_timer is not None:
			self.ping_timer.cancel()
		self.ping_timer = callLater(True, self.max_ping_timeout, self.ping_timed_out)

	def recv(self,msg):
		if msg.type is MT_IND_ACK and self.msgid is None:
			self.msgid = msg.msgid
			return RECV_AGAIN
		if msg.type is MT_IND and msg.msgid == self.msgid:
			self.ping_start()
			self.last_recv = now(True)
			return RECV_AGAIN
		if msg.type is MT_IND_NAK and msg.msgid == self.msgid:
			if self.ping_timer is not None:
				self.ping_timer.cancel()
				self.ping_timer = None
			simple_event(Context(),"wago","ping","cancel",msg.msg)
			return MINE
		if (msg.type is MT_NAK or msg.type is MT_ERROR) and self.msgid is None:
			simple_event(Context(),"wago","ping","error",msg.msg)
			return MINE
		return NOT_MINE

	def done(self):
		self.blocking = False
		if self.ping_timer is not None:
			self.ping_timer.cancel()
			self.ping_timer = None


class WAGOqueue(MsgQueue):
	"""A simple adapter for the Wago protocol."""
	storage = WAGOserver
	ondemand = False
	max_send = None

	def __init__(self, name, host,port, *a,**k):
		super(WAGOqueue,self).__init__(name=name, factory=MsgFactory(WAGOchannel,name=name,host=host,port=port, **k))

	def setup(self):
		self.enqueue(WAGOinitMsg(self))
		self.enqueue(WAGOmonitorsMsg(self))


class WAGOconnect(NetConnect):
	name = ("connect","wago")
	dest = None
	doc = "connect to a Wago server"
	port = 59995
	retry_interval = None
	max_retry_interval = None
	timeout_interval = None
	max_timeout_interval = None

	long_doc="""\
connect wago NAME [[host] port]
- connect to the wago server at the remote port;
	name that connection NAME. Defaults for host/port are localhost/59995.
	The system will emit connection-ready and device-present events.
"""

	def start_up(self):
		q = WAGOqueue(name=self.dest, host=self.host,port=self.port)
		if self.retry_interval is not None:
			q.initial_connect_timeout = self.retry_interval
		if self.max_retry_interval is not None:
			q.max_connect_timeout = self.max_retry_interval
		q.start()
		if self.timeout_interval is not None:
			msg = WAGOkeepaliveMsg(q, self.timeout_interval,self.max_timeout_interval)
			q.enqueue(msg)
WAGOconnect.register_statement(NetRetry)


class WAGOkeepalive(Statement):
	name= "keepalive"
	doc="start a keepalive timer"

	long_doc = u"""\
keepalive ‹timer› ‹timeout›
- Request a message every ‹timer› seconds; kill the connection if nothing after ‹timeout›. 
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) not in (1,2):
			raise SyntaxError(u"Usage: %s ‹timer› ‹timeout›" % (self.name,))
		try:
			self.parent.timeout_interval = float(event[0])
			if len(event) > 1:
				self.parent.max_timeout_interval = float(event[1])
		except ValueError:
			raise SyntaxError(u"Usage: %s ‹timer› ‹timeout› (#seconds, float)" % (self.name,))
WAGOconnect.register_statement(WAGOkeepalive)


class WAGOconnected(Check):
	name="connected wago"
	doc="Test if the named wago server connection is running"
	def check(self,*args):
		assert len(args)==1,"This test requires the connection name"
		try:
			bus = WAGOserver[Name(*args)]
		except KeyError:
			return False
		else:
			return bus.channel is not None

class WAGOexists(Check):
	name="exists wago"
	doc="Test if the named wago server connection exists"
	def check(self,*args):
		assert len(args)>0,"This test requires the connection name"
		return Name(*args) in WAGOserver


class WAGOdisconnect(Statement):
	name = ("disconnect","wago")
	doc = "disconnect from an WAGO server"
	long_doc="""\
disconnect wago NAME
  - disconnect from the wago server named NAME.
	The system will emit connection-closed and device-absent events.
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError("Usage: disconnect wago NAME")
		name = event[0]
		log(TRACE,"Dropping WAGO connection",name)
		bus = WAGOserver[name]
		
		log(TRACE,"Drop WAGO connection",name)


### simple variables

class WAGOrun(MsgBase):
	"""Send a simple command to Wago. Base class."""
	timeout=2

	def send(self,conn):
		conn.write(self.msg)
		return RECV_AGAIN

	def recv(self,msg):
		if msg.type is MT_ACK:
			self.result.set(msg.msg)
			return MINE
		if msg.type is MT_NAK or msg.type is MT_ERROR:
			self.result.set(WAGOerror(msg.msg))
			return MINE
		return NOT_MINE

	@property
	def msg(self):
		raise NotImplementedError("You forgot to override %s.msg"%(self.__class__.__name__,))


class WAGOioRun(WAGOrun):
	"""Send a simple I/O command to Wago."""

	def __init__(self,card,port):
		super(WAGOioRun,self).__init__()
		self.card = card
		self.port = port

	def __repr__(self):
		return "<%s %s:%s>" % (self.__class__.__name__,self.card,self.port)
		
	def list(self):
		for r in super(WAGOioRun,self).list():
			yield r
		yield ("card",self.card)
		yield ("port",self.port)

class WAGOinputRun(WAGOioRun):
	"""Send a simple command read an input."""
	@property
	def msg(self):
		return "i %d %d" % (self.card,self.port)


class WAGOoutputRun(WAGOioRun):
	"""Send a simple command to write an output."""
	def __init__(self,card,port,value):
		self.val = value
		super(WAGOoutputRun,self).__init__(card,port)

	def __repr__(self):
		res = super(WAGOoutputRun,self).__repr__()
		return "<%s val=%s>" % (res[1:-1],self.val)
		
	def list(self):
		for r in super(WAGOoutputRun,self).list():
			yield r
		yield ("value",self.val)

	@property
	def msg(self):
		return "%s %d %d" % ("s" if self.val else "c", self.card,self.port)

class WAGOoutputInRun(WAGOioRun):
	"""Send a simple command to read an output."""
	@property
	def msg(self):
		return "I %d %d" % (self.card,self.port)

class WAGOtimedOutputRun(WAGOoutputRun):
	msgid = None
	def __init__(self,queue,value,timer):
		self.queue = queue
		self.timer = timer
		super(WAGOtimedOutputRun,self).__init__(queue.card,queue.port,value)

	def __repr__(self):
		res = super(WAGOoutputRun,self).__repr__()
		return "<%s tm=%s id=%s>" % (res[1:-1],humandelta(self.timer-now(True)),self.msgid)
		
	def list(self):
		for r in super(WAGOtimedOutputRun,self).list():
			yield r
		yield ("timer",self.timer)
		yield ("id",self.msgid)

	@property
	def msg(self):
		delta = unixdelta(self.timer-now(True))
		if delta < 0.1: delta = 0.1
		return "%s %d %d %f" % ("s" if self.val else "c", self.card,self.port,delta)
	
	def recv(self,msg):
		if msg.type is MT_IND_ACK and self.msgid is None:
			self.msgid = msg.msgid
			return RECV_AGAIN
		if msg.type is MT_IND and msg.msgid == self.msgid:
			self.result.set(msg.msg)
			return RECV_AGAIN
		if msg.type is MT_IND_NAK and msg.msgid == self.msgid:
			if not self.result.ready():
				self.result.set(WAGOerror(msg.msg))
			return MINE
		if (msg.type is MT_NAK or msg.type is MT_ERROR) and self.msgid is None:
			self.result.set(WAGOerror(msg.msg))
			return MINE
		return NOT_MINE

	def error(self,err):
		log("wago",DEBUG,"Got error",self,err)
		simple_event("output","error", self.val, *self.queue.name)
		super(WAGOtimedOutputRun,self).error(err)
	
	def retry(self):
		if self.msgid is None:
			return SEND_AGAIN
		return RECV_AGAIN

class WAGOrawRun(WAGOrun):
	"""Send a simple command to write a command."""
	def __init__(self,msg):
		self._msg = msg
		super(WAGOrawRun,self).__init__()
	
	@property
	def msg(self):
		return self._msg

class WAGOio(object):
	"""Base class for Wago input and output variables"""
	typ="wago"
	def __init__(self, name, params,addons,ranges,values):
		if len(params) < 3:
			raise SyntaxError(u"Usage: %s wago ‹name…› ‹card› ‹port›"%(self.what,))
		self.server = Name(*params[:-2])
		self.card = int(params[-2])
		self.port = int(params[-1])
		super(WAGOio,self).__init__(name, params,addons,ranges,values)

	def list(self):
		for r in super(WAGOinput,self).list():
			yield r
		yield ("server",self.server)
		yield ("card",self.card)
		yield ("port",self.port)


class WAGOinput(BoolIO,WAGOio,Input):
	what="input"
	doc="An input on a remote WAGO server"

	@property
	def msg(self):
		return "i %d %d" % (self.card,self.port)

	def _read(self):
		msg = WAGOinputRun(self.card,self.port)
		WAGOserver[self.server].enqueue(msg)
		res = msg.result.get()
		if isinstance(res,Exception):
			reraise(res)
		if res == "1":
			return True
		elif res == "0":
			return False
		raise WAGObadResult(res)


class WAGOoutput(BoolIO,WAGOio,Output):
	what="output"
	doc="An output on a remote WAGO server"

	def _write(self,val):
		msg = WAGOoutputRun(self.card,self.port,val)
		WAGOserver[self.server].enqueue(msg)
		res = msg.result.get()
		if isinstance(res,Exception):
			reraise(res)
		return
	
	def _tmwrite(self,val,timer,nextval=None):
		assert nextval is None,"setting a different next value is not supported yet"
		msg = WAGOtimedOutputRun(self,val,timer)
		WAGOserver[self.server].enqueue(msg)
		res = msg.result.get()
		if isinstance(res,Exception):
			reraise(res)
		return
	
	def _read(self):
		msg = WAGOoutputInRun(self.card,self.port)
		WAGOserver[self.server].enqueue(msg)
		res = msg.result.get()
		if isinstance(res,Exception):
			reraise(res)
		if res == "1":
			return True
		elif res == "0":
			return False
		raise WAGObadResult(res)


class WAGOraw(AttributedStatement):
	name="send wago"
	dest = None
	doc="Send a line to a controller"

	long_doc = u"""\
send wago ‹name› ‹text…›
  - Send this text (multiple words are space separated) to a controller
send wago ‹text…› :to ‹name›
  - Use this form if you need to use a multi-word name
"""

	def run(self,ctx,**k):
		event = self.params(ctx)
		name = self.dest
		if name is None:
			name = Name(event[0])
			event = event[1:]
		else:
			name = Name(*name.apply(ctx))

		val = u" ".join(unicode(s) for s in event)

		msg = WAGOrawRun(val)
		WAGOserver[name].enqueue(msg)
		res = msg.result.get()


@WAGOraw.register_statement
class WAGOto(Statement):
	name=("to",)
	dest = None
	doc="specify the (multi-word) name of the connection"

	long_doc = u"""\
to ‹name…›
- Use this form for connections with multi-word names.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		self.parent.dest = SName(event)


class WAGOmon(Monitor):
	queue_len = 1 # use the watcher queue

	def __init__(self,*a,**k):
		pass
		#m = WAGOinput(slot=self.values["slot"], port=self.port)
		#servers[self].add_monitor(self)
		#super(WAGOmon,self).__init__(*a,**k)

	def submit(self,val):
		try:
			self.watcher.put(val,timeout=0)
		except Full:
			simple_event(self.ctx, "monitor","error","overrun",*self.values["params"])
			pass


class WAGOmonitor(MonitorHandler):
	name= "monitor wago"
	monitor = WAGOmon
	doc="watch (or count transitions on) an input on a wago server"
	long_doc="""\
monitor wago ‹server…› ‹slot› ‹port›
	- creates a monitor for a specific input on the server.
"""
	mode = None
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 3:
			raise SyntaxError("Usage: monitor wago ‹server…› ‹slot› ‹port›")
		self.values["slot"] = int(event[-1])
		self.values["port"] = int(event[-2])
		self.values["server"] = event[:-2]
		self.values["params"] = ("wago",)+tuple(event)
		if "switch" in self.values and self.values["switch"] is not None:
			self.values["params"] += (u"±"+unicode(self.values["switch"]),)

		super(WAGOmonitor,self).run(ctx,**k)

@WAGOmonitor.register_statement
class WAGOmonMode(Statement):
	name = "mode"
	doc = "Select whether to report or count transitions"

@WAGOmonitor.register_statement
class WAGOmonLevel(Statement):
	name = "level"
	doc = "Select which transitons to monitor"


class WAGOmodule(Module):
	"""\
		Talk to a Wago server.
		"""

	info = "Basic Wago server access"

	def load(self):
		main_words.register_statement(WAGOconnect)
		main_words.register_statement(WAGOmonitor)
		main_words.register_statement(WAGOdisconnect)
		main_words.register_statement(WAGOraw)
		register_condition(WAGOconnected)
		register_condition(WAGOexists)
		register_input(WAGOinput)
		register_output(WAGOoutput)
	
	def unload(self):
		main_words.unregister_statement(WAGOconnect)
		main_words.unregister_statement(WAGOmonitor)
		main_words.unregister_statement(WAGOdisconnect)
		main_words.unregister_statement(WAGOraw)
		unregister_condition(WAGOconnected)
		unregister_condition(WAGOexists)
		unregister_input(WAGOinput)
		unregister_output(WAGOoutput)
	
init = WAGOmodule
