# -*- coding: utf-8 -*-

"""\
This code implements (a subset of) the OWFS server protocol.

"""

from homevent.module import Module
from homevent.logging import log,log_exc,DEBUG,TRACE,INFO,WARN,ERROR
from homevent.statement import Statement, main_words
from homevent.check import Check,register_condition,unregister_condition
from homevent.context import Context
from homevent.event import Event
from homevent.run import process_event,process_failure
from homevent.reconnect import ReconnectingClientFactory
from homevent.twist import deferToLater

from twisted.internet import protocol,defer,reactor
from twisted.protocols.basic import _PauseableMixin
from twisted.python import failure

import struct
import os
import errno

OWLOG = ("HOMEVENT_LOG_ONEWIRE" in os.environ)

N_PRIO = 3
PRIO_URGENT = 0
PRIO_STANDARD = 1
PRIO_BACKGROUND = 2

PRIO_STEP = 10 # number of iterations before considering the next queue

MAX_TRIES = 3 # retrying a message until failure

def _call(_,p,*a,**k):
	return p(*a,**k)

class DisconnectedBusError(RuntimeError):
	def __init__(self,dev):
		self.dev = dev
	def __str__(self):
		return "Disconnected: %s" % (self.dev,)
	
class DisconnectedDeviceError(RuntimeError):
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

class OWFSerror(EnvironmentError):
	def __init__(self,typ):
		self.typ = typ
	def __str__(self):
		if self.typ < 0:
			try:
				return "OWFS_ERR: %d: %s" % (self.typ,errno.errorcode[-self.typ])
			except Exception:
				pass
		return "OWFS_ERR %s" % (self.typ,)

	def __repr__(self):
		return "OWFSerror(%d)" % (self.typ,)

class OWMsg:
	"""Constants for the owserver api message types."""
	error    = 0
	nop      = 1
	read     = 2
	write    = 3
	dir      = 4
	size     = 5
	presence = 6

class OWFlag:
	cache = 1 # ?
	busret = 2 # enumeration includes bus names
	persist = 4 # use persistent connections

class OWdevformat:
	fdi = 0
	fi = 1
	fdidc = 2
	fdic = 3
	fidc = 4
	fic = 5
	_offset = 24

class OWtempformat:
	celsius = 0
	fahrenheit = 1
	kelvin = 2
	rankine = 3
	_offset = 16

class OWFSreceiver(object,protocol.Protocol, _PauseableMixin):
	"""A receiver for the protocol used by OWFS.
	"""

	MAX_LENGTH = 99999
	data = ""
	typ = None
	len = 24

	def __init__(self, persist=False, *a,**k):
		self.persist = persist
		super(OWFSreceiver,self).__init__(*a,**k)

	def msgReceived(self, typ, msg):
		"""Override this.
		"""
		raise NotImplementedError

	def errReceived(self, err):
		"""Override this.
		"""
		raise NotImplementedError

	def dataReceived(self, data):
		"""Convert OWFS messages into calls to msgReceived."""
		self.data += data
		while len(self.data) >= self.len and not self.paused:
			if self.typ is None:
				version, payload_len, ret_value, format_flags, data_len, offset = struct.unpack('!6i', self.data[:24])
				self.data = self.data[24:]

				if OWLOG: print "OW RECV", version, payload_len, ret_value, format_flags, data_len, offset

				if version != 0:
					self.errReceived(RuntimeError("Wrong version: %d"%(version,)))
					return
				if payload_len == -1 and data_len == 0 and offset == 0:
					return # server busy
				if payload_len < 0 or payload_len > 0 and (payload_len < data_len or offset+data_len > payload_len):
					self.errReceived(RuntimeError("Wrong length: %d %d %d"%(payload_len,offset,data_len,)))
					return

				if payload_len > self.MAX_LENGTH:
					self.transport.loseConnection()
					self.errReceived(RuntimeError("Length exceeded: %d %d %d"%(payload_len,offset,data_len,)))
					return
				self.offset = offset
				if payload_len:
					self.data_len = data_len
				else:
					self.data_len = 0
				self.len = payload_len
				self.typ = ret_value
			else:
				data = self.data[self.offset:self.offset+self.data_len]
				self.data = self.data[self.len:]
				typ = self.typ
				self.typ = None
				self.len = 24

				self.msgReceived(typ,data)

	def sendMsg(self, typ, data, rlen):
		"""Send an OWFS message to the other end of the connection.
		"""
		flags = 0
		if self.persist:
			flags |= OWFlag.persist
		flags |= OWFlag.busret
		# flags |= 1<<8 ## ?
		flags |= OWtempformat.celsius << OWtempformat._offset
		flags |= OWdevformat.fdi << OWdevformat._offset

		if OWLOG: print "OW SEND", 0, len(data), typ, flags, rlen, 0, repr(data)
		self.transport.write(struct.pack("!6i", \
			0, len(data), typ, flags, rlen, 0) +data)



class OWFScall(object):
	"""An object representing one call to OWFS"""
	prio = PRIO_STANDARD
	empty_ok = False
	tries = 0
	max_tries = MAX_TRIES
	xconn = None

	def __init__(self):
		self.d = None
	
	def __repr__(self):
		return "‹"+self.__class__.__name__+"›"

	def _queue(self, conn):
		self.conn = conn
		if self.d is None:
			self.d = defer.Deferred()
	
	def send(self,conn):
		raise NotImplemetedError("You need to override send().")

	def sendMsg(self,conn, typ,data, rlen=0):
		d = defer.maybeDeferred(conn.sendMsg, typ,data,rlen)
		d.addErrback(self.error)

	def dataReceived(self, data):
		# child object expect this
		if OWLOG: print "OWFS done: ",self
		if self.d is not None:
			self.d.callback(data)

	def msgReceived(self, typ, data):
		if typ < 0:
			raise OWFSerror(typ)
		return self.dataReceived(data)

	def done(self, _=None):
		"""Processing is finished."""
		if self.d is not None and not self.d.called:
			raise RuntimeError("Did not trigger the result in msgReceived()",_)
	
	def error(self,err):
		"""An error occurred."""
		if not self.d.called:
			if OWLOG: print "OWFS done error: ",self,err
			self.d.errback(err)
		else:
			process_failure(err)

	def _path(self,path):
		"""Helper to build an OWFS path from a list"""
		if not path:
			return "/uncached"
		return "/uncached/"+"/".join(path)

	def may_retry(self):
		if self.d.called:
			return False
		self.tries += 1
		if self.tries < self.max_tries:
			return True
		self.error(TooManyTries(self.path))
		return False



class OWFStimeout(object):
	"""A mix-in that provides possibly-"benign" timeouts and NOP handling."""
	timeout = 1.5
	error_on_timeout = True

	def __init__(self,*a,**k):
		self.timer = None
		super(OWFStimeout,self).__init__(*a,**k)

	def has_timeout(self):
		self.timer = None
		if self.error_on_timeout:
			self.conn.conn.is_done(TimedOut(self.path))
		else:
			self.conn.conn.is_done()

	def do_timeout(self):
		if self.timer is None:
			self.timer = reactor.callLater(self.timeout,self.has_timeout)

	def drop_timeout(self):
		if self.timer:
			self.timer.cancel()
			self.timer = None
	
	def sendMsg(self,*a,**k):
		self.do_timeout()
		return super(OWFStimeout,self).sendMsg(*a,**k)

	def msgReceived(self, typ, *a,**k):
		self.drop_timeout()
#		if typ == OWMsg.nop:
#			self.do_timeout()
#			return True
#		else:
		res = super(OWFStimeout,self).msgReceived(typ,*a,**k)
		if not res:
			self.do_timeout()
		return res
	
	def error(self,*a,**k):
		self.drop_timeout()
		return super(OWFStimeout,self).error(*a,**k)

	def done(self,*a,**k):
		self.drop_timeout()
		return super(OWFStimeout,self).done(*a,**k)
	

class NOPmsg(OWFScall):
	prio = PRIO_BACKGROUND

	def send(self,conn):
		self.sendMsg(conn,OWMsg.nop,"",0)


class ATTRgetmsg(OWFStimeout,OWFScall):
	def __init__(self,path, prio=PRIO_STANDARD):
		self.path = path
		self.prio = prio
		super(ATTRgetmsg,self).__init__()

	def send(self,conn):
		self.sendMsg(conn,OWMsg.read,self._path(self.path)+'\0',8192)
	
	def __repr__(self):
		return "‹"+self.__class__.__name__+" "+self.path[-2]+" "+self.path[-1]+"›"
		
	
	# .dataReceived() already does what's expected
	

class ATTRsetmsg(OWFStimeout,OWFScall):
	def __init__(self,path,value, prio=PRIO_URGENT):
		self.path = path
		self.value = value
		super(ATTRsetmsg,self).__init__()

	def send(self,conn):
		val = str(self.value)
		self.sendMsg(conn, OWMsg.write,self._path(self.path)+'\0'+val,len(val))

	def __repr__(self):
		return "‹"+self.__class__.__name__+" "+self.path[-2]+" "+self.path[-1]+" "+str(self.value)+"›"
		


class DIRmsg(OWFStimeout,OWFScall):
	error_on_timeout = False
	prio = PRIO_BACKGROUND
	empty_ok = True

	def __init__(self,path,cb):
		self.path = path
		self.cb = cb
		super(DIRmsg,self).__init__()
	
	def send(self,conn):
		self.sendMsg(conn, OWMsg.dir, self._path(self.path)+'\0', 0)

	def dataReceived(self,data):
		if len(data):
			try: data = data[data.rindex('/')+1:]
			except ValueError: pass
			self.cb(data)
			return True
	
	def done(self, _=None):
		if OWLOG: print "OWFS doneDIR",self
		self.d.callback(_)
		return super(DIRmsg,self).done()

	def __repr__(self):
		return "‹"+self.__class__.__name__+" "+"/".join(self.path)+"›"
		
		

class OWFSqueue(OWFSreceiver):
	"""A queued version of the owfs server protocol"""

	def __init__(self, *a,**k):
		super(OWFSqueue,self).__init__(*a,**k)
		self.nop = None
		self.msg = None
		self.n_msgs = 0

	def send(self,msg):
		assert self.msg is None, "OWFS Message already in transit!"
		self.msg = msg
		if OWLOG: print "OWFS send for",self.msg
		msg.send(self)


	def connectionFailed(self,reason):
		super(OWFSqueue,self).connectionFailed(reason)
		self.retry()

	def connectionLost(self,reason):
		super(OWFSqueue,self).connectionLost(reason)
		self.is_done()

	def connectionMade(self):
		self.factory.haveConnection(self)

	def msgReceived(self, typ, data):
		if OWLOG: print "OWFS recv for %s: %d: %s"%(self.msg,typ,repr(data))
		self.n_msgs += 1
		if not self.msg:
			log(ERROR,"Spurious OWFS message",typ,data)
			return
		try:
			if self.msg.msgReceived(typ,data):
				if OWLOG: print "OWFS recv again"
				return
		except Exception,e:
			#if OWLOG: print "OWFS recv err",e
			#process_failure()
			self.is_done(e)
		else:
			if OWLOG: print "OWFS recv done"
			self.is_done()
	
	def errReceived(self,err):
		self.is_done(err)
		self.loseConnection()

	def is_done(self, res=None):
		"""Signal that the current transaction has concluded."""
		msg = self.msg
		n_msgs = self.n_msgs

		self.msg = None
		self.n_msgs = 0

		self.factory.send_done(disconnect=(res is not None or n_msgs == 0))

		if msg is None:
			if OWLOG: print "OWFS done NO_MSG",res
			return

		if OWLOG: print "OWFS done",msg.prio,self.msg,res
		if res is not None:
			self.retry(msg,res)
		elif n_msgs or msg.empty_ok:
			msg.done()
		else:
			self.retry(msg)
		

	def timeout(self, err=None):
		self.timer = None
		if err is None:
			err = RuntimeError("Timed out")
		self.is_done(err)

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
		if isinstance(err,OWFSerror) and err.typ == -errno.EINVAL:
			msg.error(err)
		elif msg.may_retry():
			deferToLater(reactor.callLater,0.5*msg.tries,self.factory.queue,msg)
		else:
			msg.error(err)



class OWFSfactory(object,ReconnectingClientFactory):

	protocol = OWFSqueue

	def __init__(self, host="localhost", port=4304, persist = False, name=None, *a,**k):
		if name is None:
			name = "%s:%s" % (host,port)

		self.conn = None
		self.host = host
		self.port = port
		self.name = name
		self._init_queues()
		self.persist = persist
		self.up_event = False
		self.root = OWFSroot(self)
		self.watcher_id = None
		self.nop = None
		self.trace_retry = OWLOG

	def _init_queues(self):
		self.queues = []
		self.q_prio = []
		for x in range(N_PRIO):
			self.queues.append([PRIO_STEP])

	def has_queued(self):
		for s in self.queues:
			if len(s) > 1:
				return True
		return False

	def get_queued(self):
		for i in (0,1):
			for s in self.queues:
				if len(s) > 1:
					if s[0]:
						s[0] += -1
						return s.pop(1)
					else:
						s[0] = PRIO_STEP
		return NOPmsg()

	def queue(self,msg):
		if OWLOG: print "OWFS queue",msg.prio,msg
		if not self.continueTrying:
			return defer.fail(DisconnectedBusError(self.name))

		self.queues[msg.prio].append(msg)
		msg._queue(self)
		self.maybe_connect()
		return msg.d

	def maybe_connect(self):
		if not self.conn:
			self.tryNow()
		elif self.persist and not self.conn.msg:
			self.conn.send(self.get_queued())

	def send_done(self, disconnect=False):
		if self.persist and not disconnect:
			self.send_next()
		elif self.conn:
			self.conn.loseConnection()
	
	def send_next(self, force=True):
		if force or self.has_queued():
			if self.nop:
				self.nop.cancel()
				self.nop = None
			self.conn.send(self.get_queued())

		elif not self.nop:
			if self.persist:
				delay = 10
			else:
				delay = 300
			self.nop = reactor.callLater(delay,self.nopper)

	def nopper(self):
		self.nop = None
		self.queue(NOPmsg()).addErrback(process_failure)

	def finalFailure(self):
		if self.up_event:
			self.up_event = False
			process_event(Event(Context(),"onewire","disconnect",self.name),return_errors=True).addErrback(process_failure)

	def clientConnectionFailed(self, connector, reason):
		self.conn = None
		log(WARN,reason)
		super(OWFSfactory,self).clientConnectionFailed(connector, reason)
		process_event(Event(Context(),"onewire","broken", self.name),return_errors=True).addErrback(process_failure)

	def clientConnectionLost(self, connector, reason):
		self.conn = None
		if self.persist:
			log(INFO,reason)
		else:
			if OWLOG: log(TRACE,reason)

		if self.has_queued():
			connector.connect()
		elif self.persist:
			super(OWFSfactory,self).clientConnectionFailed(connector, reason)
		else:
			self.connector = connector


	def haveConnection(self,conn):
		self.resetDelay()
		self.conn = conn

		if not self.up_event:
			self.up_event = True
			process_event(Event(Context(),"onewire","connect",self.name),return_errors=True).addErrback(process_failure)

		conn.send(self.get_queued())

	def _drop(self):
		e = DisconnectedBusError(self.name)
		q = self.queues
		self.queues = []
		for s in q:
			for r in s[1:]:
				r.error(e)

		if self.conn:
			self.conn.loseConnection()

	def drop(self):
		"""Kill my connection and forget any devices"""
		self.stopTrying()
		if self.conn and self.conn.msg:
			def d(_):
				self._drop()
				return _
			self.conn.msg.d.addBoth(d)
		else:
			self._drop()
		

	def all_devices(self, proc):
		def doit(dev,path=(),key=None):
			buses = []
			entries = []
			def got_entry(name):
				if key is None and name.startswith("bus."):
					buses.append(name)
				else:
					entries.append(name)

			def done(_):
				f = defer.succeed(None)
				if buses:
					for b in buses:
						f.addCallback(_call,doit,dev,path=path+(b,),key=None)
				else:
					p = dev.path
					if dev.bus_id:
						p += (dev.bus_id,)
					p += path
					if key:
						p += (key,)

					for b in entries:
						dn = OWFSdevice(id=b,bus=self,path=p)
						f.addCallback(_call,proc,dn)
						if b.startswith("1F."): # Bus multiplexer
							f.addCallback(_call,doit,dn,key="main")
							f.addCallback(_call,doit,dn,key="aux")
				return f

			e = dev.dir(key=key,proc=got_entry,path=path)
			e.addCallback(done)
			return e

		return doit(self.root)

	def update_all(self):
		d = process_event(Event(Context(),"onewire","scanning",self.name),return_errors=True)
		d.addCallback(_call,self._update_all)
		d.addErrback(process_failure)
		return d

	def _update_all(self):
		log(TRACE,"OWFS start bus update")
		old_ids = devices.copy()
		new_ids = {}
		seen_ids = {}
		def got_dev(dev):
			if dev in seen_ids:
				return
			if dev.id in old_ids:
				del old_ids[dev.id]
			else:
				new_ids[dev.id] = dev
			seen_ids[dev.id] = dev
		d = self.all_devices(got_dev)

		def cleanup(_):
			e = defer.succeed(None)
			for dev in old_ids.itervalues():
				if dev.bus is self:
					dev.go_down()
			
			def dropit(_,dev):
				del devices[dev.id]
				return process_failure(_)

			for dev in new_ids.itervalues():
				if not hasattr(dev,"typ"):
					e.addCallback(_call,dev.get,"type")
					e.addCallback(dev._setattr,"typ")
				e.addCallback(_call,dev.go_up)
				e.addErrback(dropit,dev)

			def num(_):
				process_event(Event(Context(),"onewire","scanned",self.name,len(old_ids), len(new_ids), len(devices)),return_errors=True).addErrback(process_failure)
				return len(old_ids)
			e.addCallback(num)
			return e
			
		d.addCallback(cleanup)
		def lerr(_):
			log(TRACE,"OWFS done bus update (with error)")
			return _
		d.addErrback(lerr)
		return d
	
	def watcher(self):
		self.watcher_id = True
		d = defer.succeed(None)
		d.addCallback(_call,self.update_all)
		def monitor(_):
			if "HOMEVENT_TEST" in os.environ:
				if _: d = 10
				else: d = 30
			else:
				if _: d = 60
				else: d = 300
			self.watcher_id = reactor.callLater(d,self.watcher)
		d.addCallbacks(monitor,process_failure)
	
	def run_watcher(self):
		if self.watcher_id is not True:
			if self.watcher_id is not None:
				self.watcher_id.cancel()
			self.watcher()



ow_buses = {}

def connect(host="localhost", port=4304, name=None, persist=False):
	assert (host,port) not in ow_buses, "already known host/port tuple"
	f = OWFSfactory(host=host, port=port, name=name, persist=persist)
	ow_buses[(host,port)] = f
	reactor.connectTCP(host, port, f)
	f.run_watcher()
	return f

def disconnect(f):
	assert f==ow_buses.pop((f.host,f.port))
	f.drop()


devices = {}

_call_id = 0


class OWFSdevice(object):
	"""This represents a bus device with attributes."""
	def __new__(cls,id, bus=None, path=()):
		short_id = id[id.index(".")+1:]
		try:
			self = devices[short_id]
		except KeyError: # new device
			self = super(OWFSdevice,cls).__new__(cls)
			self._init(bus, short_id,id ,path)
			devices[short_id] = self
			return self
		else: # old device, found again
			if bus is not None and hasattr(self,'typ'):
				self.bus = bus
				self.path = path
				self.go_up()
			return self

	def _init(self, bus, short_id=None, id=None, path=()):
		if OWLOG: print "OW NEW", bus,short_id,id,path
		self.bus_id = id
		self.id = short_id
		self.bus = bus
		self.path = path
		self.is_up = None
		self.ctx = Context()
       
	def _setattr(self,val,key):
		"""Helper. Needed for new devices to set the device type."""

		setattr(self,key,val)

	def __repr__(self):
		if not hasattr(self,'path') and not hasattr(self,'id'):
			return "‹OW root›"
		else:
			return "‹OW:%s %s›" % (self.id,self.path)

	def go_up(self):
		if self.is_up:
			return
		d = defer.succeed(None)
		if self.is_up is None:
			d.addCallback(_call,process_event,Event(self.ctx,"onewire","new",self.typ,self.id))
		self.is_up = True
		d.addCallback(_call,process_event,Event(self.ctx,"onewire","up",self.typ,self.id))
		return d

	def go_down(self, _=None):
		if not self.is_up:
			return
		self.is_up = False
		if _ is not None:
			d = process_failure(_)
		else:
			d = defer.succeed(None)

		if _ is None:
			d.addBoth(_call,process_event,Event(self.ctx,"onewire","down",self.typ,self.id))
		else:
			# if this happened during a call, the "down" event may only
			# complete processing after the call has returned the error,
			# which causes an inconvenient deadlock.
			def do_down(_):
				process_event(Event(self.ctx,"onewire","down",self.typ,self.id),return_errors=True).addErrback(process_failure)
				return _
			d.addBoth(do_down)

		return d


	def get(self,key):
		if not self.bus:
			raise DisconnectedDeviceError(self.id)

		msg = ATTRgetmsg(self.path+(self.bus_id,key))
		self.bus.queue(msg)

		def got(_):
			try:
				_ = int(_)
			except ValueError:
				try:
					_ = float(_)
				except ValueError:
					pass
			return _
		msg.d.addCallback(got)

		def down(_):
			self.go_down(_)
			return _
		msg.d.addErrback(down)
		return msg.d


	def set(self,key,val):
		if not self.bus:
			raise DisconnectedDeviceError(self.id)

		msg = ATTRsetmsg(self.path+(self.bus_id,key),val)
		self.bus.queue(msg)
		msg.d.addErrback(self.go_down)
		return msg.d


	def dir(self, proc, path=(), key=None):
		if not self.bus:
			raise DisconnectedDeviceError(self.id)

		p = self.path + tuple(path)
		if self.bus_id is not None:
			p += (self.bus_id,)
		if key is not None:
			p += (key,)
		msg = DIRmsg(p,proc)
		self.bus.queue(msg)
		msg.d.addErrback(self.go_down)
		return msg.d


class OWFSroot(OWFSdevice):
	"""Represents the root device of an owfs tree"""
	def __new__(cls,bus):
		self = object.__new__(cls)
		self._init(bus)
		return self

