# -*- coding: utf-8 -*-

##
##  Copyright © 2012-2008, Matthias Urlichs <matthias@urlichs.de>
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
This code implements generic message queueing across a channel.

Your code needs to supply message converters and "real" connections.
Look at module/onewire.py for an example.
"""

from homevent.logging import log,log_exc,DEBUG,TRACE,INFO,WARN,ERROR
from homevent.statement import Statement, main_words, AttributedStatement
from homevent.check import Check,register_condition,unregister_condition
from homevent.context import Context
from homevent.event import Event
from homevent.base import Name,singleName
from homevent.run import process_failure,simple_event
from homevent.collect import Collection,Collected
from homevent.twist import fix_exception,reraise, callLater,Jobber
from homevent.net import DisconnectedError
from homevent.times import now

import os
import sys
import socket

import gevent
from gevent.queue import PriorityQueue
from gevent.event import AsyncResult

N_PRIO = 3
PRIO_CONNECT = -1
PRIO_URGENT = 0
PRIO_STANDARD = 1
PRIO_BACKGROUND = 2

class MSG_ERROR(object):
	"""Drop the message."""
	def __init__(self,txt):
		self.txt = txt
	def __repr__(self):
		return "%s(%s)" % (self.__class__.__name__, repr(self.txt))
	__str__ = __repr__
class ABORT(singleName):
	"""Handshake failed; kill the connection"""
	pass
class NOT_MINE(singleName):
	"""Not my message."""
	pass
class MINE(singleName):
	"""My message. Don't keep me in the receiver queue."""
	pass
class SEND_AGAIN(singleName):
	"""My message. I will send more messages."""
	pass
class RECV_AGAIN(singleName):
	"""My message. I will receive more messages."""
class SEND_LATER(object):
	"""My message. I will send more messages later."""
	# TODO
	pass
#	def __init__(self,delay):
#		self.delay = delay
#	def queue(self,msg,chan):
#		self.msg = msg
#		self.chan = chan
#		self.timer = callLater(False,self._call)
#		self.chan.delayed.append(self.timer)
#	def _call(self):
#		self.timer = None
#		self.chan.enqueue(self.msg)
#	def unqueue(self):
#		del self.chan.delayed[self.timer]
#		self.timer.cancel()
#		self.timer = None


class MsgSender(object):
	"""A message sender"""
	prio = PRIO_STANDARD
	def queue(self,bus):
		bus.enqueue(self)

	def send(self,channel):
		"""write myself to the channel. Return None|SEND_AGAIN"""
		raise NotImplementedError("You need to override MsgSender.send")

	def done(self):
		pass

class MsgReceiver(object):
	"""A receiver, possibly for a broadcast message"""
	prio = PRIO_STANDARD
	def recv(self,data):
		"""A message has been received. Return NOT_MINE|MINE|RECV_AGAIN."""
		raise NotImplementedError("You need to override MsgReceiver.recv")
	
	def abort(self):
		"""The channel could not send the message."""
		pass

	def retry(self):
		"""\
			The channel had to be set up again. Return None|SEND_AGAIN|RECV_AGAIN.
			(None removes the receiver from the queue.)
			"""
		pass
	
	def done(self):
		pass
	
class NoAnswer(RuntimeError):
	"""The server does not reply."""
	no_backtrace = True
	def __init__(self,conn):
		self.conn = conn
	def __str__(self):
		return "%s: %s" % (self.__class__.__name__,self.conn)

class MsgBase(MsgSender,MsgReceiver):
	"""A message which expects a reply."""
	timeout = None
	blocking = False # True if the message needs a reply before sending more

	timeout = None
	_timer = None
	_last_channel = None
	_send_err = None
	_recv_err = None
	
	def __init__(self,*a,**k):
		super(MsgBase,self).__init__(*a,**k)
		self.result = AsyncResult()

	def send(self,channel):
		"""write myself to the channel. Return None|SEND_AGAIN|RECV_AGAIN."""
		self._set_timeout()
		self._last_channel = channel

		if self._send_err is None:
			self._send_err = MSG_ERROR("You need to override %s.send"%self.__class__.__name__)
		return self._send_err
	
	def recv(self,data):
		"""A message has been received. Return NOT_MINE|MINE|RECV_AGAIN|SEND_AGAIN."""
		self._clear_timeout()

		if self._recv_err is None:
			self._recv_err = MSG_ERROR("You need to override %s.recv"%self.__class__.__name__)
		return self._recv_err
	
	def retry(self):
		"""Check whether to retry this message"""
		self._clear_timeout()
		return False

	def done(self):
		"""Processing is finished."""
		self._clear_timeout()
		if self.result is not None and not self.result.successful():
			raise RuntimeError("Did not trigger the result in %s.dataReceived()"%(self.__class__.__name__,))

	def do_timeout(self):
		self._last_channel.close()
		
	def _set_timeout(self):
		if self.timeout is not None:
			self._timer = callLater(True,self.timeout,self._timeout)

	def _clear_timeout(self):
		if self._timer is not None:
			self._timer.cancel()
			self._timer = None
	
	def _timeout(self):
		self._timer = None
		self.do_timeout()
		
class MsgRepeater(object):
	"""A message mix-in that's repeated periodically; useful for keepalive"""
	timer = None

	redo_timeout = 60 # how often to repeat

	queue = None # MsgQueue that is broken

	def __init__(self,queue):
		super(MsgRepeater,self).__init__()
		self.queue = queue

	def send(self,channel):
		self.disarm()
		res = super(MsgBase,self).send(channel)
		self.arm(True)
		return res
	
	def disarm(self):
		if self.timer is not None:
			self.timer.cancel()
			self.timer = None
	
	def arm(self,sending):
		if self.timer is None:
			self.timer = callLater(True,self.reply_timeout,self.send_me)
	
	def send_me(self):
		self.timer = None
		self.queue.enqueue(self)
	
	def retry(self):
		self.disarm()
		return True

class MsgIncoming(object):
	"""Wrapper to signal an incoming message"""
	def __init__(self,**k):
		for a,b in k.iteritems():
			setattr(self,a,b)
		if not hasattr(self,"prio"):
			if hasattr(self,"msg") and hasattr(self.msg,"prio"):
				self.prio = self.msg.prio
			else:
				self.prio = PRIO_STANDARD

	def __str__(self):
		s = " ".join(["%s:%s" % (k,repr(v)) for k,v in self.__dict__.iteritems()])
		return u"‹%s%s%s›" % (self.__class__.__name__, ": " if s else "", s)

class MsgError(object):
	"""Wrapper to signal an error assembling an incoming message"""
	prio = PRIO_CONNECT
	def __init__(self,error):
		self.error = error

class MsgReOpen(object):
	"""Signal to (close and) re-open the connection"""
	prio = PRIO_CONNECT
	pass

class MsgFactory(object):
	"""\
		Build a message forwarder from a channel type (and its init arguments).

		This is usually called as:

			>>>	class MYchannel(MYassembler, NetActiveConnector):
			...		'''A receiver for the protocol used by OWFS.'''
			...		storage = MYchans
			>>>
			>>> class MYqueue(MsgQueue):
			... 	'''A simple adapter for the MY protocol.'''
			... 	storage = MYservers
			... 	ondemand = True
			... 	max_send = None
			... 	
			... 	def __init__(self, name, host,port, *a,**k):
			... 		super(MYqueue,self).__init__(name=name, factory=MsgFactory(MYchannel,name=name,host=host, port=port, **k)) 

		where MYassembler implements dataReceived(), which ultimately calls msgReceived(),
		which is a method added via MsgFactory.
		"""

	def __init__(self,cls,*a,**k):
		"""\
			Setup a factory to create a new channel.
			A channel is created by calling @cls with the rest of the supplied arguments when needed.
			"""
		class _MsgForwarder(cls):
			def __init__(self,q):
				self._msg_queue = q
				super(_MsgForwarder,self).__init__(*a,**k)
			def __repr__(self):
				return u"‹%s:%s›" % (cls.__name__,cls.__repr__(self))
			def msgReceived(self,**k):
				msg = MsgIncoming(**k)
				self._msg_queue.put((msg.prio,msg))
			def error(self,msg):
				msg = MsgError(msg)
				self._msg_queue.put((msg.prio,msg))
			def up_event(self,*a,**k):
				
				pass
			def not_up_event(self,external=False,*a,**k):
				if external:
					msg = MsgReOpen()
					self._msg_queue.put((msg.prio,msg))
			def down_event(self,external=False,*a,**k):
				if external:
					msg = MsgReOpen()
					self._msg_queue.put((msg.prio,msg))
		self.cls = _MsgForwarder

	def __call__(self,q):
		return self.cls(q)
		
		

class BadResult(RuntimeError):
	"""a message receiver returned something inconclusive"""
	pass

class UnknownMessageType(RuntimeError):
	"""could not determine what to do with this"""
	pass

class MsgQueue(Collected,Jobber):
	"""\
		This class represents a persistent network connection.
		Message objects are queued to instances of this class.
		They and can set up long-term interactions with whatever is at the remote end.
		Connection (re)establishment is handled (mostly) transparently.

		This is a subclass of @Collected, so you need to supply a 'storage' class attribute.
		"""
	#storage = Nets.storage
	max_open = None # outstanding messages
	max_send = None # messages to send until the channel is restarted
	max_connect = None # connection attempts
	connect_timer = 3 # delay between attempts
	max_connect_timer = 300 # max delay between attempts

	channel = None # the current connection
	job = None # the queue handler greenlet
	factory = None # a callable that builds a new channel
	ondemand = False # only open a connection when we have messages to send?

	name = None
	state = "New"
	last_change = None

	n_sent = 0
	n_rcvd = 0
	n_processed = 0
	n_sent_now = 0
	n_rcvd_now = 0
	n_processed_now = 0
	last_sent = None
	last_sent_at = None
	last_rcvd = None
	last_rcvd_at = None

	def __init__(self, factory, name, qlen=None, ondemand=None):
		self.name = name
		self.factory = factory
		self.msgs = [] # to send
		self.delayed = []
		self.receivers = []
		for _ in range(N_PRIO):
			self.msgs.append([])
		self.q = PriorityQueue(maxsize=qlen)

		if ondemand is not None:
			self.ondemand = ondemand
		self.start()

		super(MsgQueue,self).__init__()
	
	def __del__(self):
		self.stop_job("job")

	def start(self):
		"""Start running the handler"""
		self.start_job("job",self._handler)

	def stop(self,reason="stopped"):
		self.stop_job("job")
		self._teardown(reason)

	def enqueue(self,msg):
		if not self.job:
			self.start()
		self.q.put((msg.prio,msg), block=False)

	def setup(self):
		"""Send any initial messages to the channel"""
		pass

	def delete(self,ctx=None):
		self.stop("deleted")
		for m in self.delayed[:]:
			m.unqueue()
		self.delete_done()

	def info(self):
		return unicode(self)
	def __repr__(self):
		return u"‹%s:%s %s›" % (self.__class__.__name__,self.name,self.state)
                
	def list(self):
		yield ("state",self.state)
		yield ("since",self.last_change)
		yield ("sent",self.n_sent,self.n_sent_now)
		yield ("received",self.n_rcvd,self.n_rcvd_now)
		yield ("processed",self.n_processed,self.n_processed_now)
		yield ("open",self.is_open)
		if self.last_sent is not None:
			yield ("last_sent",self.last_sent)
			yield ("last_sent_at",self.last_sent_at)
		if self.last_rcvd is not None:
			yield ("last_rcvd",self.last_rcvd)
			yield ("last_rcvd_at",self.last_rcvd_at)
		yield ("in_queued",self.q.qsize())
		yield ("out_queued",self.n_outq)
		for d in self.delayed:
			yield ("delayed",str(d))
		if self.channel:
			for a,b in self.channel.list():
				yield ("conn "+a,b)
		# now dump send and recv queues
		i = 0
		for mq in self.msgs:
			for m in mq:
				yield("msg send "+str(i),repr(m))
			i += 1
		for m in self.receivers:
			yield("msg recv",repr(m))


	def _incoming(self,msg):
		"""Process an incoming message."""
		self.n_rcvd += 1
		log("conn",TRACE,"incoming", self.__class__.__name__,self.name,msg)
		self.last_recv = msg
		self.last_recv_at = now()

		# i is an optimization for receiver lists that don't change in mid-action
		i = 0
		handled = False
		for m in self.receivers:
			try:
				log("msg",TRACE,"recv",self.name,str(msg))
				r = m.recv(msg)
				log("msg",TRACE,"recv=",r)
				if r is ABORT:
					self.close(False)
					break
				elif r is NOT_MINE:
					continue
				elif r is MINE or r is SEND_AGAIN:
					handled = True
					if len(self.receivers) > i and self.receivers[i] is m:
						self.receivers.pop(i)
					else:
						self.receivers.remove(m)

					if r is SEND_AGAIN:
						if m.blocking:
							self.msgs[0].insert(0,m)
						else:
							self.msgs[m.prio].append(m)
					else:
						m.done()
						self.n_processed_now += 1
						if self.max_send is not None and self.max_send >= self.n_processed_now:
							self.enqueue(MsgReOpen())
					break
				elif r is RECV_AGAIN:
					handled = True
					break
				elif r is SEND_AGAIN:
					handled = True
					break
				elif isinstance(r,MSG_ERROR):
					raise r
				else:
					raise BadResult(m)
			except Exception as ex:
				if len(self.receivers) < i and self.receivers[i] is m:
					self.receivers.pop(i)
				elif m in self.receivers:
					self.receivers.remove(m)
				fix_exception(ex)
				process_failure(ex)

				self.close(False)
			i += 1
		if not handled:
			simple_event(Context(),"msg","unhandled",str(msg),*self.name)

	def _error(self,msg):
		log("conn",ERROR,self.state,self.__class__.__name__,self.name,str(msg))
		self._teaddown()
		process_failure(msg)
		
	def _set_state(self,state):
		log("conn",TRACE,state,self.__class__.__name__,self.name)
		self.state = state
		self.last_change = now()

	def _setup(self):
		attempts = 0
		timeout = self.connect_timer
		try:
			self._set_state("connecting")
			self.channel = self.factory(self.q)
			self._set_state("setting up")
			self.setup()
			if self.state == "setting up":
				self._set_state("connected")
		except Exception as ex:
			fix_exception(ex)
			log_exc("Setting up",ex)

			self._teardown("retrying")
			attempts += 1
			if self.max_connect is not None and attempts > self.max_connect:
				self._set_state("too many connection attempts")
				for m in self.receivers:
					m.abort()
				raise
			gevent.sleep(timeout)
			timeout *= 1.6
			if self.max_connect_timer is not None and timeout > self.max_connect_timer:
				timeout = self.max_connect_timer
		else:
			self.n_rcvd += self.n_rcvd_now
			self.n_rcvd_now = 0
			self.n_sent += self.n_sent_now
			self.n_sent_now = 0
			self.n_processed += self.n_processed_now
			self.n_processed_now = 0

			recvs = self.receivers
			self.receivers = []
			for m in recvs:
				try:
					r = m.retry()
					if r is SEND_AGAIN:
						self.msgs[msg.prio].append(msg)
					elif r is RECV_AGAIN:
						self.receivers.append(msg)
						pass
					elif r is not None:
						raise RuntimeError("Strange retry(): %s %s" % (repr(msg),repr(r)))
				except Exception as e:
					fix_exception(e)
					process_failure(e)
					self.receivers.remove(m)
					m.error(e)

	def _teardown(self, reason="closed", external=False):
		if self.channel:
			self.state="closing"
			self.channel.delete()
			self.channel = None
			self._set_state(reason)

	@property
	def is_open(self):
		"""Count the number of outstanding messages"""
		res = 0
		for m in self.receivers:
			if isinstance(m,MsgBase):
				res += 1
		return res

	@property
	def n_outq(self):
		n=0
		for mq in self.msgs:
			n += len(mq)
		return n

	def _handler(self):
		"""\
			This is the receiver's main loop.

			Processing of incoming and outgoing data is serialized so that
			there will be no problems with concurrency.
			"""
		if not self.ondemand:
			m = MsgReOpen()
			self.q.put((m.prio,m), block=False)
		while True:
			_,msg = self.q.get()
			if isinstance(msg,MsgSender):
				self.msgs[msg.prio].append(msg)
			elif isinstance(msg,MsgReceiver):
				if msg.blocking:
					self.receivers.insert(0,msg)
				else:
					self.receivers.append(msg)
			elif isinstance(msg,MsgIncoming):
				self._incoming(msg)
			elif isinstance(msg,MsgReOpen):
				self._teardown("ReOpen",external=False)
			elif isinstance(msg,MsgError):
				self._error(msg.error)
			else:
				raise UnknownMessageType(msg)

			if self.ondemand and not self.n_outq:
				continue
			if not self.channel:
				self._setup()

			done = False # marker for "don't send any more stuff"

			for m in self.receivers:
				if m.blocking:
					done = True
					break

			for mq in self.msgs:
				if done:
					break
				if self.max_open >= self.is_open:
					break
				while len(mq):
					m = mq.pop(0)
					r = m.send(self.channel)
					self.last_sent = m
					self.last_sent_at = now()
					if r is RECV_AGAIN:
						if m.blocking:
							self.receivers.insert(0,m)
						else:
							self.receivers.append(m)
					elif r is SEND_AGAIN:
						self.msgs[msg.prio].append(msg)
					elif isinstance(r,SEND_LATER):
						raise NotImplementedError("Queueing doesn't work yet")
					elif isinstance(r,MSG_ERROR):
						try:
							raise r
						except Exception as r:
							fix_exception(r)
							process_failure(r)
					else:
						msg.done()

					if m.blocking:
						done = True
						break
				
