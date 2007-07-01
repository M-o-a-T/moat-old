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
from twisted.internet import protocol,defer,reactor
from twisted.protocols.basic import _PauseableMixin
from twisted.python import failure
import struct

N_PRIO = 3
PRIO_URGENT = 0
PRIO_STANDARD = 1
PRIO_BACKGROUND = 2

def _call(_,p,*a,**k):
	return p(*a,**k)

class DisconnectedError(RuntimeError):
	def __init__(self,dev):
		self.dev = dev
	def __str__(self):
		return "Disconnected: %s" % (self.dev,)
	
class TimedOut(RuntimeError):
	def __init__(self,id,key):
		self.id = id
		self.key = key
	def __str__(self):
		return "Timeout: No data at %s/%s" % (self.id,self.key)

class OWFSerror(EnvironmentError):
	def __init__(self,typ):
		self.typ = typ
	def __str__(self):
		if self.typ < 0:
			try:
				from errno import errorcode
				return "OWFS_ERR: %d: %s" % (self.typ,errorcode[self.typ])
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

	An int32 string is a string prefixed by 4 bytes, the 32-bit length of
	the string encoded in network byte order.

	This class publishes the same interface as NetstringReceiver.
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

	def dataReceived(self, data):
		"""Convert OWFS messages into calls to msgReceived."""
		#log(TRACE,"OWFS recv %d"%len(data))
		self.data += data
		while len(self.data) >= self.len and not self.paused:
			if self.typ is None:
				version, payload_len, ret_value, format_flags, data_len, offset = struct.unpack('!6i', self.data[:24])
				self.data = self.data[24:]

				log(TRACE, "OW RECV", version, payload_len, ret_value, format_flags, data_len, offset)
				if payload_len > self.MAX_LENGTH:
					self.transport.loseConnection()
					return
				self.offset = offset
				self.data_len = data_len
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
		# flags |= 1<<8 ## ?
		flags |= OWtempformat.celsius << OWtempformat._offset
		flags |= OWdevformat.fdi << OWdevformat._offset

		log(TRACE, "OW SEND", 0, len(data), typ, flags, rlen, 0, repr(data))
		self.transport.write(struct.pack("!6i", \
			0, len(data), typ, flags, rlen, 0) +data)



class OWFScall(object):
	"""An object representing one call to OWFS"""
	prio = PRIO_STANDARD

	def __init__(self):
		pass
	
	def __repr__(self):
		return "‹"+self.__class__.__name__+"›"

	def _queue(self, conn):
		self.conn = conn
		self.d = defer.Deferred()
	
	def send(self):
		raise NotImplemetedError("You need to override send().")

	def sendMsg(self,typ,data, rlen=0):
		 d = defer.maybeDeferred(self.conn.sendMsg,typ, data, rlen)
		 d.addErrback(self.error)

	def dataReceived(self, data):
		# child object expect this
		self.d.callback(data)

	def msgReceived(self, typ, data):
		if typ < 0:
			raise OWFSerror(typ)
		return self.dataReceived(data)

	def done(self, _=None):
		"""Processing is finished."""
		if not self.d.called:
			raise RuntimeError("Did not trigger the result in msgReceived()",_)
	
	def error(self,msg):
		"""An error occurred."""
		if not self.d.called:
			self.d.errback(msg)
		else:
			process_failure(msg)

	def _path(self,path):
		"""Helper to build an OWFS path from a list"""
		if not path:
			return "/uncached"
		return "/uncached/"+"/".join(path)



class OWFStimeout(object):
	"""A mix-in that provides possibly-"benign" timeouts."""
	timeout = 1.5
	error_on_timeout = True

	def __init__(self,*a,**k):
		self.timer = None
		super(OWFStimeout,self).__init__(*a,**k)

	def has_timeout(self):
		self.timer = None
		if self.error_on_timeout:
			self.error(TimedOut())
		else:
			self.done()
		self.conn._is_done()

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

	def msgReceived(self, *a,**k):
		self.drop_timeout()
		return super(OWFStimeout,self).msgReceived(*a,**k)
	
	def error(self,*a,**k):
		self.drop_timeout()
		return super(OWFStimeout,self).error(*a,**k)

	def done(self,*a,**k):
		self.drop_timeout()
		return super(OWFStimeout,self).done(*a,**k)


class NOPmsg(OWFScall):
	prio = PRIO_BACKGROUND

	def send(self):
		self.sendMsg(OWMsg.nop,"",0)


class ATTRgetmsg(OWFScall):
	def __init__(self,path, prio=PRIO_STANDARD):
		self.path = path
		self.prio = prio
		super(ATTRgetmsg,self).__init__()

	def send(self):
		self.sendMsg(OWMsg.read,self._path(self.path)+'\0',8192)
	
	def __repr__(self):
		return "‹"+self.__class__.__name__+" "+self.path[-2]+" "+self.path[-1]+"›"
		
	
	# .dataReceived() already does what's expected
	

class ATTRsetmsg(OWFScall):
	def __init__(self,path,value, prio=PRIO_URGENT):
		self.path = path
		self.value = value
		super(ATTRsetmsg,self).__init__()

	def send(self):
		self.sendMsg(OWMsg.write,self._path(self.path)+'\0'+str(self.value)+'\0',0)

	def __repr__(self):
		return "‹"+self.__class__.__name__+" "+self.path[-2]+" "+self.path[-1]+" "+str(self.value)+"›"
		


class DIRmsg(OWFStimeout,OWFScall):
	error_on_timeout = False
	prio = PRIO_BACKGROUND

	def __init__(self,path,cb):
		self.path = path
		self.cb = cb
		super(DIRmsg,self).__init__()
	
	def send(self):
		self.sendMsg(OWMsg.dir, self._path(self.path)+'\0', 0)

	def dataReceived(self,data):
		if len(data):
			try: data = data[data.rindex('/')+1:]
			except ValueError: pass
			self.cb(data)
			return True
	
	def done(self, _=None):
		self.d.callback(_)

	def __repr__(self):
		return "‹"+self.__class__.__name__+" "+"/".join(self.path)+"›"
		
		

class OWFSqueue(OWFSreceiver):
	"""A queued version of the owfs server protocol"""

	def __init__(self, *a,**k):
		super(OWFSqueue,self).__init__(*a,**k)
		self.root = OWFSroot(self)
		self.queues = []
		for x in range(N_PRIO): self.queues.append([])
		self.nop = None
		self.open = None
		self.watcher_id = None
		self.n_msgs = 0
		self.n_calls = 0
		self.up_event = False

	def connectionFailed(self,reason):
		if self.up_event:
			self.up_event = False
			process_event(Event(Context(),"onewire","disconnect",self._factory.host,self._factory.port)).addErrback(process_failure)

		if not self._factory.continueTrying:
			self._factory.resetDelay()

		if self.nop:
			self.nop.cancel()
			self.nop = None

		dl = []
		for dev in ow_devices.itervalues():
			if dev.bus is self:
				dev.bus = None
				dl.append(dev)
		for dev in dl:
			dev.go_down()

		super(OWFSqueue,self).connectionFailed(reason)

		if self.open:
			self.open.error(reason)
			self.open = None

		q = self.queues
		self.queues = []
		for x in range(N_PRIO): self.queues.append([])

		for s in q:
			for t in s:
				t.error(reason)

	def connectionLost(self,reason):
		if self.open and not self.persist:
			if self.n_msgs > 0:
				self.open.done()
			else:
				self.open.error(reason)
			self.open = None

		if self.n_calls < 3:
			self.persist = False # grumble

		super(OWFSqueue,self).connectionLost(reason)


	def connectionMade(self):
		if not self.up_event:
			self.up_event = True
			process_event(Event(Context(),"onewire","connect",self._factory.host,self._factory.port)).addErrback(process_failure)

		super(OWFSqueue,self).connectionMade()
		self._factory.resetDelay()

		self.n_msgs = 0
		self.n_calls = 0
		if self.open:
			self.n_calls += 1
			self.open.send()
		else:
			self._do_next()

		if self.open is None:
			self.n_calls = 0
			if not self.nop:
				self.nop = reactor.callLater(1,self.nopper)

	def nopper(self):
		self.nop = None
		msg = NOPmsg()
		self.queue(msg)
		msg.d.addErrback(process_failure)

	def _do_next(self):
		if self.nop:
			self.nop.cancel()
			self.nop = None

		if self.open is not None:
			return
		for s in self.queues:
			if s:
				self.open = s.pop(0)
				break

		if self.transport and not self.persist and self.n_calls:
			self.transport.loseConnection()

		if not self.open:
			if not self.nop:
				if self.persist:
					delay = 10
				else:
					delay = 300
					self._factory.stopTrying()
				self.nop = reactor.callLater(delay,self.nopper)
			return

		if self.transport is None:
			if not self.persist:
				log(TRACE,"OWFS reconnect now",self.open.prio,self.open)
				if self._factory.connector is not None:
					self._factory.stopTrying()
					self._factory.connector.connect()
			else:
				log(TRACE,"OWFS reconnect WAIT",self.open.prio,self.open)

		elif self.persist or not self.n_calls:
			log(TRACE,"OWFS run",self.open.prio,self.open)
			self.n_calls += 1
			self.open.send()

	def queue(self,msg):
		log(TRACE,"OWFS queue",msg.prio,msg)
		self.queues[msg.prio].append(msg)
		msg._queue(self)
		self._do_next()
		return msg.d

	def msgReceived(self, typ, data):
		log(TRACE,"OWFS recv for %s: %d: %s"%(self.open,typ,repr(data)))
		self.n_msgs += 1
		if not self.open:
			log(ERROR,"Spurious OWFS message",typ,data)
			return
		try:
			if self.open.msgReceived(typ,data):
				return
		except Exception,e:
			self.open.error(e)
		else:
			self.open.done()
		self._is_done()
	
	def _is_done(self):
		"""Signal that the current transaction has concluded."""
		log(TRACE,"OWFS done",self.open.prio,self.open)
		self.open = None
		self.n_msgs = 0

		if self.persist:
			self._do_next()

	def timeout(self, err=None):
		self.timer = None
		if err is None:
			err = RuntimeError("Timed out")
		self.open.error(err)


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
					if dev.id:
						p += (dev.id,)
					p += path
					if key:
						p += (key,)

					for b in entries:
						dn = OWFSdevice(id=b,bus=self,path=p)
						f.addCallback(_call,proc,dn)
						if b.startswith("1F."): # Bus adapter
							f.addCallback(_call,doit,dn,key="main")
							f.addCallback(_call,doit,dn,key="aux")
				return f

			e = dev.dir(key=key,proc=got_entry,path=path)
			e.addCallback(done)
			return e

		return doit(self.root)

	def update_all(self):
		log(TRACE,"OWFS start bus update")
		old_ids = ow_devices.copy()
		new_ids = {}

		def got_dev(dev):
			if dev in old_ids:
				del old_ids[dev.id]
			else:
				new_ids[dev.id] = dev
		d = self.all_devices(got_dev)

		def cleanup(_):
			e = defer.succeed(None)
			for dev in old_ids.itervalues():
				if dev.bus is self:
					dev.go_down()
			
			def dropit(_,dev):
				del ow_devices[dev.id]
				process_failure(_)

			for dev in new_ids.itervalues():
				if not hasattr(dev,"typ"):
					e.addCallback(_call,dev.get,"type")
					e.addCallback(dev._setattr,"typ")
				e.addCallback(lambda _,dev: dev.go_up(), dev)
				e.addErrback(dropit,dev)
			return e
			
		d.addCallback(cleanup)
		d.addCallback(_call,log,TRACE,"OWFS done bus update")
		def lerr(_):
			log(TRACE,"OWFS done bus update (with error)")
			return _
		d.addErrback(lerr)
		return d
	
	def watcher(self):
		self.watcher_id = True
		d = defer.succeed(None)
		d.addCallback(_call,self.update_all)
		d.addErrback(process_failure)
		def monitor(_):
			self.watcher_id = reactor.callLater(300,self.watcher)
		d.addCallback(monitor)
	
	def run_watcher(self):
		if self.watcher_id is None:
			self.watcher()


class OWFSfactory(object,protocol.ReconnectingClientFactory):

    protocol = OWFSqueue

    def clientConnectionFailed(self, connector, reason):
		log(WARN,reason)
		super(OWFSfactory,self).clientConnectionFailed(connector, reason)

    def clientConnectionLost(self, connector, reason):
		q = self.protocol()
		if q.persist:
			log(INFO,reason)
		else:
			log(TRACE,reason)
		super(OWFSfactory,self).clientConnectionLost(connector, reason)
		q._do_next()
		if q.open:
			self.stopTrying()
			connector.connect()


ow_buses = {}

def connect(host="localhost", port=4304, persist=False):
	assert (host,port) not in ow_buses, "already known host/port tuple"
	f = OWFSfactory()
	q = OWFSqueue(persist=persist)
	q._factory = f
	def retq():
		return q
	f.protocol = retq
	f.host = host
	f.port = port
	ow_buses[(host,port)] = f
	reactor.connectTCP(host, port, f)

	q.run_watcher()



ow_devices = {}

_call_id = 0


class OWFSdevice(object):
	"""This represents a bus device with attributes."""
	def __new__(cls,id, bus=None, path=()):
		try:
			self = ow_devices[id]
		except KeyError: # new device
			self = super(OWFSdevice,cls).__new__(cls)
			self._init(id,bus,path)
			ow_devices[id] = self
			return self
		else: # old device, found again
			if bus is not None:
				self.bus = bus
				self.path = path
				self.go_up()
			return self

	def _init(self,id, bus,path=()):
		self.id = id
		self.bus = bus
		self.path = path
		self.is_up = None
		self.ctx = Context()
		
	def _setattr(self,val,key):
		"""Helper. Needed for new devices to set the device type."""
		setattr(self,key,val)

	def __repr__(self):
		if not self.path and not self.id:
			return "<OW root>"
		else:
			return "<OW:%s %s>" % (self.id,self.path)

	def go_up(self):
		if self.is_up:
			return
		d = defer.succeed(None)
		if self.is_up is None:
			d.addCallback(lambda _: process_event(Event(self.ctx,"onewire","new",self.typ,self.id)))
		self.is_up = True
		d.addCallback(lambda _: process_event(Event(self.ctx,"onewire","up",self.typ,self.id)))
		return d

	def go_down(self, _=None):
		if not self.is_up:
			return
		self.is_up = False
		return process_event(Event(self.ctx,"onewire","down",self.typ,self.id))


	def get(self,key):
		if not self.bus:
			raise DisconnectedError(self)

		msg = ATTRgetmsg(self.path+(self.id,key))
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
		msg.d.addErrback(self.go_down)
		return msg.d


	def set(self,key,val):
		if not self.bus:
			raise DisconnectedError(self)

		msg = ATTRsetmsg(self.path+(self.id,key),val)
		self.bus.queue(msg)
		msg.d.addErrback(self.go_down)
		return msg.d


	def dir(self, proc, path=(), key=None):
		if not self.bus:
			raise DisconnectedError(self)

		p = self.path + path
		if self.id is not None:
			p += (self.id,)
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
		self._init(None,bus)
		return self

