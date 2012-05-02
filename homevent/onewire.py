# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2012, Matthias Urlichs <matthias@urlichs.de>
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
This code implements (a subset of) the OWFS server protocol.

"""

from homevent import TESTING
from homevent.module import Module
from homevent.logging import log,log_exc,DEBUG,TRACE,INFO,WARN,ERROR
from homevent.statement import Statement, main_words
from homevent.check import Check,register_condition,unregister_condition
from homevent.context import Context
from homevent.collect import Collection
from homevent.event import Event
from homevent.run import process_event,process_failure,simple_event
from homevent.twist import callLater, fix_exception,print_exception, Jobber
from homevent.base import Name
from homevent.net import NetActiveConnector
from homevent.msg import MsgReceiver,MsgBase,MsgQueue,MsgFactory,\
	PRIO_STANDARD,PRIO_URGENT,PRIO_BACKGROUND,\
	SEND_AGAIN,RECV_AGAIN,MINE,NOT_MINE

import struct
import os
import errno
import sys

import gevent
from gevent.event import AsyncResult
from gevent.queue import Queue,Empty

PRIO_STEP = 10 # number of iterations before considering the next queue

MAX_TRIES = 5 # retrying a message until failure

PERSIST=True # Default

class DisconnectedDeviceError(RuntimeError):
	"""A devince has vanished."""
	no_backtrace = True
	def __init__(self,dev):
		self.dev = dev
	def __str__(self):
		return "%s: %s" % (self.__class__.__name__,self.dev)
	
class OWMsg:
	"""Constants for the owserver api message types."""
	error    = 0
	nop      = 1
	read     = 2
	write    = 3
	dir      = 4
	size     = 5
	presence = 6
	dirall   = 7
	get      = 8

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


class OWFSassembler(object):
	"""A mix-in object which can do assembly and dissassembly of OWFS messages."""
	MAX_LENGTH = 99999
	_data = ""
	_typ = None
	_len = 24

	def __init__(self,persist=PERSIST,*a,**k):
		self.persist = persist
		super(OWFSassembler,self).__init__(*a,**k)
		
	def error(self,err):
		self.close()
		raise NotImplementedError("You need to override OWFSassembler.error")

	def msgReceived(self,err):
		self.close()
		raise NotImplementedError("You need to override OWFSassembler.msgReceived")

	def dataReceived(self, data):
		"""Convert OWFS messages into calls to msgReceived."""
		self._data += data
		while len(self._data) >= self._len:
			if self._typ is None:
				version, payload_len, ret_value, format_flags, data_len, offset = struct.unpack('!6i', self._data[:24])
				self._data = self._data[24:]

				log("onewire",DEBUG,"RECV", version, payload_len, ret_value, format_flags, data_len, offset)
				# 0 253 0 2 252 32774
				if offset & 32768: offset = 0

				if version != 0:
					self.error(RuntimeError("Wrong version: %d"%(version,)))
					return
				if payload_len == -1 and data_len == 0 and offset == 0:

					return # server busy
#				if payload_len < 0 or payload_len > 0 and (payload_len < data_len or offset+data_len > payload_len):
#					self.errReceived(RuntimeError("Wrong length: %d %d %d"%(payload_len,offset,data_len,)))
#					return

				if payload_len > self.MAX_LENGTH:
					self.error(RuntimeError("Length exceeded: %d %d %d"%(payload_len,offset,data_len,)))
					return
				self._offset = offset
				if payload_len:
					self._data_len = data_len
				else:
					self._data_len = 0
				self._len = payload_len
				self._typ = ret_value
			else:
				data = self._data[self._offset:self._offset+self._data_len]
				self._data = self._data[self._len:]
				typ = self._typ
				self._typ = None
				self._len = 24

				self.msgReceived(typ=typ,data=data)

	def sendMsg(self, typ, data, rlen):
		"""Send an OWFS message to the other end of the connection.
		"""
		flags = 0
		if self.persist:
			flags |= OWFlag.persist
		# needed for sometimes-broken 1wire daemons
		flags |= OWFlag.busret
		# flags |= 1<<8 ## ?
		flags |= OWtempformat.celsius << OWtempformat._offset
		flags |= OWdevformat.fdi << OWdevformat._offset

		log("onewire",DEBUG,"SEND", 0, len(data), typ, flags, rlen, 0, repr(data))
		self.write(struct.pack("!6i", \
			0, len(data), typ, flags, rlen, 0) +data)


class OWchans(Collection):
       name = "owfs connection"
OWchans = OWchans()
OWchans.does("del")
OWchans2 = {}

class OWFSchannel(OWFSassembler, NetActiveConnector):
	"""A receiver for the protocol used by OWFS."""
	storage = OWchans
	storage2 = OWchans2

	def down_event(self, external=False):
			simple_event(Context(),"onewire","disconnect",*self.name)

	def up_event(self, external=False):
			simple_event(Context(),"onewire","connect",*self.name)

	def not_up_event(self, external=False):
			simple_event(Context(),"onewire","error",*self.name)


class OWFSxmit(object):
	"""A mixin that sends messages"""

	def sendMsg(self,conn, typ,data, rlen=0):
		try:
			conn.sendMsg(typ,data,rlen)
		except Exception as ex:
			fix_exception(ex)
			self.error(ex)


class OWFScall(OWFSxmit,MsgBase):
	"""An object representing one call to OWFS"""
	prio = PRIO_STANDARD
	retries = 10
	cached = False
	timeout = 10
	d = None

	def __repr__(self):
		return u"‹"+self.__class__.__name__+u"›"

	def dataReceived(self, data):
		# child object expect this
		log("onewire",DEBUG,"done: ",self)
		if self.result is not None:
			self.result.set(data)

	def recv(self, msg):
		super(OWFScall,self).recv(msg)
		r = self.dataReceived(msg.data)
		if r is None:
			r = MINE
		return r
	
	def retry(self):
		super(OWFScall,self).retry()
		if self.retries:
			self.retries -= 1
			return SEND_AGAIN
		return None

	def error(self,err):
		"""An error occurred."""
		if self.result is not None and not self.result.successful:
			log("onewire",DEBUG,"done error: ",self,err)
			self.result.set_exception(err)
		else:
			process_failure(err)

	def _path(self,path):
		"""Helper to build an OWFS path from a list"""
		if self.cached:
			if not path:
				return ""
			return "/"+"/".join(path)
		else:
			if not path:
				return "/uncached"
			return "/uncached/"+"/".join(path)


class NOPmsg(OWFScall):
	prio = PRIO_BACKGROUND

	def send(self,conn):
		super(NOPmsg,self).send(conn)
		self.sendMsg(conn,OWMsg.nop,"",0)


class ATTRgetmsg(OWFScall):
	def __init__(self,path, prio=PRIO_STANDARD):
		assert path is not None
		self.path = path
		self.prio = prio
		super(ATTRgetmsg,self).__init__()

	def send(self,conn):
		super(ATTRgetmsg,self).send(conn)
		self.sendMsg(conn,OWMsg.read,self._path(self.path)+'\0',8192)
		return RECV_AGAIN
	
	def __repr__(self):
		return "‹"+self.__class__.__name__+" "+self.path[-2]+" "+self.path[-1]+"›"
		
	
	# .dataReceived() already does what's expected
	

class ATTRsetmsg(OWFScall):
	def __init__(self,path,value, prio=PRIO_URGENT):
		assert path is not None
		self.path = path
		self.value = value
		super(ATTRsetmsg,self).__init__()

	def send(self,conn):
		super(ATTRsetmsg,self).send(conn)
		val = unicode(self.value)
		self.sendMsg(conn, OWMsg.write,self._path(self.path)+'\0'+val,len(val))
		return RECV_AGAIN

	def __repr__(self):
		return u"‹"+self.__class__.__name__+" "+self.path[-2]+" "+self.path[-1]+" "+unicode(self.value)+u"›"
		


class DIRmsg(OWFScall):
	error_on_timeout = False
	prio = PRIO_BACKGROUND
	empty_ok = True
	cached = True
	dirall = True

	def __init__(self,path,cb):
		assert path is not None
		self.path = path
		self.cb = cb
		super(DIRmsg,self).__init__()
	
	def send(self,conn):
		super(DIRmsg,self).send(conn)
		if self.dirall:
			self.sendMsg(conn, OWMsg.dirall, self._path(self.path)+'\0', 0)
		else:
			self.sendMsg(conn, OWMsg.dir, self._path(self.path)+'\0', 0)
		return RECV_AGAIN

	def dataReceived(self,data):
		if self.dirall:
			n=0
			for entry in data.split(","):
				n += 1
				try: entry = entry[entry.rindex('/')+1:]
				except ValueError: pass
				self.cb(entry)
			self.result.set(n)
		else:
			if len(data):
				try: data = data[data.rindex('/')+1:]
				except ValueError: pass
				self.cb(data)
				return RECV_AGAIN
			self.result.set(n)
	
	### TODO: retry with "dir" if the server does not understand "dirall"
	def done(self, _=None):
		log("onewire",DEBUG,"doneDIR",self)
		return super(DIRmsg,self).done()

	def __repr__(self):
		return "‹"+self.__class__.__name__+" "+"/".join(self.path)+"›"
		
class OWbus(Collection):
       name = "owfs bus"
OWbus = OWbus()
OWbus.does("del")


class OWFSqueue(MsgQueue,Jobber):
	"""\
		An adapter for the owfs server protocol.

		The only real change is to periodically scan the bus.
		MsgQueue and the factory handle everything else.
		"""
	storage = OWbus
	ondemand = True

	def __init__(self, name, host,port, persist=PERSIST, *a,**k):
		self.ident = (host,port)
		super(OWFSqueue,self).__init__(name=name, factory=MsgFactory(OWFSchannel,name=name,host=host,port=port,persist=persist, **k))
		if not persist:
			self.max_send = 1
		self.nop = None
		self.root = OWFSroot(self)

	### Bus scanning support

	def start(self):
		super(OWFSqueue,self).start()
		self.watch_q = Queue()
		self.start_job("watcher",self._watcher)
		def dead(_):
			self._clean_watched()
		self.watcher.link(dead)

	def stop(self,reason=None):
		self.stop_job("watcher")
		super(OWFSqueue,self).stop(reason=reason)

	def _clean_watched(self):
		while True:
			try:
				q = self.watch_q.get()
			except Empty:
				break
			else:
				q.set_exception(RuntimeError("Stopped"))
		self.watch_q = None

	def all_devices(self):
		seen_mplex = {}
		def doit(dev,path=(),key=None):
			buses = []
			entries = []
			def got_entry(name):
				if key is None and name.startswith("bus."):
					buses.append(name)
				elif len(name)>3 and name[2] == ".":
					entries.append(name)
				else:
					log(TRACE,"got unrecognized OWFS name %s" % (name,))

			dev.dir(key=key,proc=got_entry,path=path)

			if buses:
				for b in buses:
					for res in doit(dev,path=path+(b,),key=None):
						yield res
				return

			p = dev.path
			if dev.bus_id:
				p += (dev.bus_id,)
			p += path
			if key:
				p += (key,)

			for b in entries:
				dn = OWFSdevice(id=b,bus=self,path=p)
				yield dn
				if b.startswith("1F.") and b not in seen_mplex:
					seen_mplex[b] = f
					for res in doit(dn,key="main"):
						yield res
					for res in doit(dn,key="aux"):
						yield res

		return doit(self.root)

	def update_all(self):
		try:
			process_event(Event(Context(),"onewire","scanning",self.name))
			self._update_all()
		except Exception as e:
			fix_exception(e)
			process_failure(e)

	def _update_all(self):
		log(TRACE,"OWFS start bus update")
		old_ids = devices.copy()
		new_ids = {}
		seen_ids = {}

		for dev in self.all_devices():
			if dev.id in seen_ids:
				continue
			seen_ids[dev.id] = dev
			if dev.id in old_ids:
				del old_ids[dev.id]
			else:
				new_ids[dev.id] = dev

		n_old = 0
		n_dev = 0
		for dev in old_ids.itervalues():
			if dev.bus is self:
				n_old += 1
				## Just because something vanishes from the listing
				## doesn't mean it's dead; the bus may be a bit unstable
				# dev.go_down()
				log(DEBUG,"Bus unstable?",self.name,dev.id)

		for dev in devices.itervalues():
			if dev.bus is self:
				n_dev += 1
		
		for dev in new_ids.itervalues():
			if not hasattr(dev,"typ"):
				try:
					t = dev.get("type")
					dev._setattr(t,"typ")
				except Exception as ex:
					del devices[dev.id]
					fix_exception(ex)
					process_failure(ex)

		simple_event(Context(),"onewire","scanned",self.name,n_old, len(new_ids), n_dev)
			
	def _watcher(self):
		res = []
		while True:
			try:
				self.update_all()
			except Exception as ex:
				fix_exception(ex)
				process_failure(ex)
				resl = len(res)
				while res:
					q = res.pop()
					q.set_exception(ex)
			else:
				resl = len(res)
				while res:
					q = res.pop()
					q.set(None)

			if TESTING:
				if resl: d = 10
				else: d = 30
			else:
				if resl: d = 60
				else: d = 300

			while True:
				try:
					q = self.watch_q.get(timeout=(d if not res else 0))
				except Empty:
					break
				else:
					res.append(q)

	def run_watcher(self):
		res = AsyncResult()
		self.watch_q.put(res)
		return res.get()



ow_buses = {}

# factory.
def connect(host="localhost", port=4304, name=None, persist=PERSIST):
	"""\
		Set up a queue to a OneWire server.
		"""
	assert (host,port) not in ow_buses, "already known host/port tuple"
	f = OWFSqueue(host=host, port=port, name=name, persist=persist)
	ow_buses[(host,port)] = f
	f.start()
	return f

def disconnect(f):
	assert f==ow_buses.pop(f.ident)
	f.stop()



devices = {}

class OWFSdevice(object):
	"""This represents a bus device with attributes."""
	def __new__(cls,id, bus=None, path=()):
		short_id = id[id.index(".")+1:].lower()
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
		log("onewire",DEBUG,"NEW", bus,short_id,id,path)
		self.bus_id = id
		if short_id:
			self.id = short_id.lower()
		self.bus = bus
		assert path is not None
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
		if self.is_up is None:
			process_event(Event(self.ctx,"onewire","new",self.typ,self.id))
		self.is_up = True
		process_event(Event(self.ctx,"onewire","up",self.typ,self.id))

	def go_down(self, _=None):
		if not self.is_up:
			return
		self.is_up = False
		if _ is not None:
			process_failure(_)
		process_event(Event(self.ctx,"onewire","down",self.typ,self.id))

	def get(self,key):
		if not self.bus:
			raise DisconnectedDeviceError(self.id)

		msg = ATTRgetmsg(self.path+(self.bus_id,key))
		msg.queue(self.bus)

		try:
			res = msg.result.get()
		except Exception as ex:
			fix_exception(ex)
			self.go_down(ex)
			raise

		try:
			res = int(res)
		except (ValueError,TypeError):
			try:
				res = float(res)
			except (ValueError,TypeError):
				pass

		return res


	def set(self,key,val):
		if not self.bus:
			raise DisconnectedDeviceError(self.id)

		msg = ATTRsetmsg(self.path+(self.bus_id,key),val)
		msg.queue(self.bus)
		try:
			return msg.result.get()
		except Exception as ex:
			fix_exception(ex)
			self.go_down(ex)


	def dir(self, proc, path=(), key=None):
		if not self.bus:
			raise DisconnectedDeviceError(self.id)

		p = self.path + Name(*path)
		if self.bus_id is not None:
			p += (self.bus_id,)
		if key is not None:
			p += (key,)

		msg = DIRmsg(p,proc)
		msg.queue(self.bus)

		try:
			return msg.result.get()
		except Exception as ex:
			fix_exception(ex)
			self.go_down(ex)


class OWFSroot(OWFSdevice):
	"""Represents the root device of an owfs tree"""
	def __new__(cls,bus):
		self = object.__new__(cls)
		self._init(bus)
		return self

