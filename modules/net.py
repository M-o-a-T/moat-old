# -*- coding: utf-8 -*-

"""\
This code implements a simple line-oriented protocol via TCP.

"""

from homevent.module import Module
from homevent.logging import log,log_exc,DEBUG,TRACE,INFO,WARN,ERROR
from homevent.statement import Statement, main_words
from homevent.check import Check,register_condition,unregister_condition
from homevent.run import process_failure
from homevent.context import Context
from homevent.event import Event
from homevent.run import process_event,process_failure
from homevent.reconnect import ReconnectingClientFactory
from homevent.twist import deferToLater

from twisted.python import failure
from twisted.internet import protocol,defer,reactor
from twisted.protocols.basic import LineReceiver,_PauseableMixin

import os

NETLOG = ("HOMEVENT_LOG_NET" in os.environ)

def _call(_,p,*a,**k):
	return p(*a,**k)

class DisconnectedError(RuntimeError):
	def __init__(self,dev):
		self.dev = dev
	def __str__(self):
		return "Disconnected: %s" % (self.dev,)
	
class idErr(RuntimeError):
	def __init__(self,path):
		self.path = path

class TimedOut(idErr):
	def __str__(self):
		return "Timeout: No data at %s" % (self.path,)

class TooManyTries(idErr):
	def __str__(self):
		return "Too many retries: at %s" % (self.path,)

class NETerror(EnvironmentError):
	def __init__(self,typ):
		self.typ = typ
	def __str__(self):
		if self.typ < 0:
			try:
				from errno import errorcode
				return "NET_ERR: %d: %s" % (self.typ,errorcode[self.typ])
			except Exception:
				pass
		return "NET_ERR %s" % (self.typ,)

	def __repr__(self):
		return "NETerror(%d)" % (self.typ,)

class NETreceiver(object,LineReceiver, _PauseableMixin):
	"""A receiver for the line protocol.
	"""

	delimiter = "\n"

	def __init__(self,name,*a,**k):
		super(NETreceiver,self).__init__(*a,**k)
		self.name = name

	def lineReceived(self, line):
		"""Override this.
		"""
		line = line.strip().split()
		process_event(Event(Context(),"net", self.name, *line), return_errors=True).addErrback(process_failure)

	def loseConnection(self):
		if self.transport:
			self.transport.loseConnection()
		self.retry()

	def retry(self,msg=None, err=None):
		if msg is None:
			msg = self.msg
			self.msg = None
		if not msg:
			return
		if msg.may_retry():
			deferToLater(reactor.callLater,0.5*msg.tries,self.factory.queue,msg)
		else:
			msg.error(err)



class NETfactory(object,ReconnectingClientFactory):

	protocol = NETqueue

	def __init__(self, host="localhost", port=4304, persist = False, name=None, *a,**k):
		if name is None:
			name = "%s:%s" % (host,port)

		self.conn = None
		self.host = host
		self.port = port
		self.name = name
		self.up_event = False
		self.trace_retry = NETLOG

	def clientConnectionFailed(self, connector, reason):
		self.conn = None
		log(WARN,reason)
		super(NETfactory,self).clientConnectionFailed(connector, reason)
		process_event(Event(Context(),"net","broken", self.name)).addErrback(process_failure)

	def clientConnectionLost(self, connector, reason):
		self.conn = None
		log(INFO,reason)

		connector.connect()

	def haveConnection(self,conn):
		self.conn = conn

		if not self.up_event:
			self.up_event = True
			process_event(Event(Context(),"net","connect",self.name)).addErrback(process_failure)

	def _drop(self):
		if self.conn:
			self.conn.loseConnection()

	def drop(self):
		"""Kill my connection and forget any devices"""
		self.stopTrying()
		self._drop()
		

net_conns = {}

def connect(host="localhost", port=None, name=None, persist=False):
	assert port is not None, "Need to provide a port number"
	assert name is not None, "Need to provide a name"
	assert (host,port) not in net_conns, "already known host/port tuple"
	assert name not in net_conns, "already known name"
	f = NETfactory(host=host, port=port, name=name, persist=persist)
	net_conns[(host,port)] = f
	net_conns[name] = f
	reactor.connectTCP(host, port, f)
	return f

def disconnect(f):
	assert f==net_conns.pop((f.host,f.port))
	assert f==net_conns.pop(f.name)
	f.drop()


def setup_receiver(name):
	def recv(*a,**k):
		return NETreceiver(name,*a,**k)
	return recv

class NETfactory(object,protocol.ReconnectingClientFactory):

	def __init__(self,name):
    	self.protocol = setup_receiver(name)
		super(NETfactory,self).__init__()


    def clientConnectionFailed(self, _, reason):
		log(INFO,reason)
		super(NETfactory,self).clientConnectionFailed(_, reason)

    def clientConnectionLost(self, _, reason):
		log(WARN,reason)
		super(NETfactory,self).clientConnectionLost(_, reason)


class NETconnect(Statement):
	name = ("connect","net")
	doc = "connect to an NET server"

	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) < 2 or len(event) > 3:
			raise SyntaxError("Usage: connect net ‹name› ‹host›? ‹port›")
		name = event[0]
		if len(event) == 2:
			host = "localhost"
		else:
			host = event[0]
		port = event[-1]

		f = NETfactory(name)
		reactor.connectTCP(host, port, f)


class NETsend(Statement):
	name=("send","net")
	doc="send a line to a NET device"
	long_doc="""\
send net name text...
	: The text is sent to the named net connection.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		name = event[0]
		val = " ".join(str(s) for s in tuple(event[1:]))
		
		d = net_conns[name].sendMsg(NETMsg.write,"/"+"/".join(str(x) for x in name)+'\0'+str(val)+'\0',0)
		return d


class NETdisconnect(Statement):
	name=("disconnect","net")
	doc="send a line to a NET device"
	long_doc="""\
disconnect net ‹name›
	: The named net connection is broken.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError("Usage: disconnect net ‹name›")
		name = event[0]
		disconnect(net_conns[name])

class NETlist(Statement):
	name=("list","net")
	doc="list known network connections"
	long_doc="""\
list net ‹name›?
	: List all network connections.
      If a name (or host/port pair) is given, lists details of that
      connection.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) == 1
			conn = net_conns(event[0])
		elif len(event) == 2:
			conn = net_conns((event[0],event[1]))
		elif len(event):
			raise SyntaxError("Usage: disconnect net ‹name›")
		else:
            for a,b in net_conns.iteritems():
				if isinstance(a,tuple): continue
                print >>ctx.out,b.name,b.host,b.port
            print >>ctx.out,"."
			return

		print "Name:",conn.name
		print "Host:",conn.host
		print "Port:",conn.port
		print >>ctx.out,"."

class NETconnected(Check):
    name=("connected","net")
    doc="Test if a net server connection exists"
    def check(self,*args):
        assert not args,"This test doesn't take arguments"
        return fh_conn is not None


class NETmodule(Module):
	"""\
		This is a sample loadable module.
		"""

	info = "Basic one-wire access"

	def load(self):
		main_words.register_statement(NETconnect)
		main_words.register_statement(NETdisconnect)
		main_words.register_statement(NETsend)
		main_words.register_statement(NETlist)
		register_condition(NETconnected)
	
	def unload(self):
		main_words.unregister_statement(NETconnect)
		main_words.unregister_statement(NETdisconnect)
		main_words.unregister_statement(NETsend)
		main_words.unregister_statement(NETlist)
		unregister_condition(NETconnected)
	
init = NETmodule
