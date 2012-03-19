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
from homevent.base import Name
from homevent.run import process_failure
from homevent.collect import Collection,Collected
from homevent.twist import fix_exception,reraise, callLater
from homevent.net import DisconnectedError
from homevent.times import now

import os
import sys
import socket

import gevent
from gevent.queue import Queue

N_PRIO = 3
PRIO_URGENT = 0
PRIO_STANDARD = 1
PRIO_BACKGROUND = 2

class NOT_MINE:
	"""Not my message."""
	pass
class MINE:
	"""My message. Don't keep me in the receiver queue."""
	pass
class AGAIN:
	"""My message. I will receive more messages."""
	pass

class MsgReceiver(object):
	"""A receiver for a broadcast message"""
	def recv(self,data):
		"""A message has been received. Return NOT_MINE|MINE|AGAIN."""
		raise NotImplementedError("You need to override MsgReceiver.recv")
	
	def abort(self):
		"""The channel could not send the message."""
		pass

	def retry(self):
		"""\
			The channel had to be set up again. Return True if you want to re-submit yourself. \
			Return False if you want to remove yourself from the receiver queue.
			"""
		pass
	
class MsgBase(MsgReceiver):
	"""A message, probably one which expects a reply."""
	timeout = None
	prio = P_STANDARD
	blocking = False # True if the message needs a reply before sending more
	
	def send(self,channel):
		"""write myself to the channel. Return None if you did nothing, True if you want to receive somrthing, False otherwise."""
		raise NotImplementedError("You need to override MsgMase.send")
	
	def recv(self,data):
		"""A message has been received. Return True if you want more."""
		raise NotImplementedError("You need to override MsgMase.recv")
		
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
		super(MsgBase,self).send(channel)
		self.arm(True)
	
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
	def __init__(self,msg):
		self.msg = msg

class MsgError(object):
	"""Wrapper to signal an error assembling an incoming message"""
	def __init__(self,error):
		self.error = error

class MsgReOpen(object):
	"""Signal to (close and) re-open the connection"""
	pass

class MsgFactory(object):
	"""Build a message forwarder from a channel type (and its init arguments)"""
	def __init__(self,chantype,*a,**k):
		class _MsgForwarder(cls):
			def __init__(self,q):
				self._msg_queue = q
				super(_MsgForwarder,self).__init__(*a,**k)
			def msgReceived(self,msg):
				self._msg_queue.enqueue(MsgIncoming(msg))
			def errReceived(self,msg):
				self._msg_queue.enqueue(MsgError(msg))
				
		self.cls = _MsgForwarder
	def __call__(self,q):
		return self.cls(q)
		
		

class BadResult(RuntimeError):
	"""a message receiver returned something inconclusive"""
	pass

class UnknownMessageType(RuntimeError):
	"""could not determine what to do with this"""
	pass

class MsgQueue(Collected):
	"""This class represents a persistent network connection."""
	#storage = Nets.storage
	#storage2 = net_conns
	max_open = None # outstanding messages
	max_send = None # messages to send until the channel is restarted
	max_connect = None # connection attempts
	connect_timer = 3 # delay between attempts
	channel = None
	factory = None # something that builds a new channel

	name = None
	state = "New"
	last_change = None

	n_sent = 0
	n_rcvd = 0
	n_sent_now = 0
	n_rcvd_now = 0
	last_sent = None
	last_sent_at = None
	last_rcvd = None
	last_rcvd_at = None

	def __init__(self, factory, name, qlen=None):
		self.name = name
		self.factory = factory
		self.msgs = [] # to send
		self.receivers = []
		for _ in range(N_PRIO):
			self.msgs.append([])
		self.q = Queue(maxsize=qlen)
		self.channel = self.factory()
		self.job = None
		super(MsgQueue,self).__init__()
	
	def __del__(self):
		if self.job:
			self.job.kill()

	def start(self):
		"""Start running the handler"""
		if self.job is not None:
			return
		self.job = gevent.spawn(self._handler)

		def died(e):
			fix_exception(e)
			report_failure(e)
		self.job.link_exception(died)
		def ended(_):
			self.job = None
		self.job.link(ended)

	def stop(self,reason="stopped"):
		if self.job:
			self.job.kill()
		self._teardown(reason)

	def enqueue(self,msg):
		if not self.job:
			self.start()
		self.q.put(msg, block=False)

	def setup(self):
		"""Send any initial messages to the channel"""
		pass

	def delete(self):
		self.stop("deleted")
		self.delete_done()

	def info(self):
		return unicode(self)
	def __repr__(self):
		return "<%s: %s>" % (self.__class__.__name__,self.state)
                
	def list(self):
		yield ("state",self.state)
		yield ("since",self.last_change)
		yield ("sent",self.n_sent,self.n_sent_now)
		yield ("received",self.n_rcvd,self.n_rcvd_now)
		yield ("open",self.is_open)
		if self.last_xmit is not None:
			yield ("last_sent",self.last_xmit)
			yield ("last_sent_at",self.last_xmit_at)
		if self.last_rcvd is not None:
			yield ("last_rcvd",self.last_rcvd)
			yield ("last_rcvd_at",self.last_rcvd_at)

	def _incoming(self,msg):
		"""Process an incoming message."""
		self.n_rcvd += 1
		log("conn",TRACE,"incoming", self.__class__.__name__,self.name,msg)
		self.last_recv = msg
		self.last_recv_at = now()

		# i is an optimization for receiver lists that don't change in mid-action
		i = 0
		for m in self.receivers:
			r = m.recv(msg)
			try:
				if r is NOT_MINE:
					continue
				elif r is MINE:
					if len(self.receivers) < i and self.receivers[i] is m:
						self.receivers.pop(i)
					else:
						self.receivers.remove(m)
					self.n_processed_now += 1
					if self.max_send is not None and self.max_send >= self.self.n_processed_now:
						self.enqueue(MsgReOpen)
					break
				elif r is AGAIN:
					break
				else:
					raise BadResult(m)
			except Exception as ex:
				if len(self.receivers) < i and self.receivers[i] is m:
					self.receivers.pop(i)
				elif m in self.receivers:
					self.receivers.remove(m)
				fix_exception(ex)
				process_failure(ex)
			i += 1

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
			self.channel = self.factory(self)
			self._set_state("setting up")
			self.setup(channel)
			if self.state == "setting up":
				self._set_state("connected")
		except Exception as ex:
			self._teardown("retrying")
			attempts += 1
			if self.max_connect is not None and attempts > self.max_connect:
				self._set_state("too many connection attempts")
				for m in self.receivers:
					m.abort()
				raise
			gevent.sleep(timeout)
			timeout *= 1.6
		else:
			self.n_rcvd += self.n_rcvd_now
			self.n_rcvd_now = 0
			self.n_sent += self.n_sent_now
			self.n_sent_now = 0
			for m in self.receivers[:]:
				try:
					r = m.retry()
					if r is True:
						self.enqueue(msg)
					elif r is False:
						self.receivers.remove(m)
				except Exception as e:
					fix_exception(e)
					self.receivers.remove(m)
					m.errReceived(e)

	def _teardown(self, reason="closed"):
		if self.channel:
			self.state="closing"
			self.channel.close()
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

	def _handler(self):
		while True:
			msg = self.q.get()
			if isinstance(msg,MsgBase):
				self.msgs[msg.prio].append(msg)
			elif isinstance(msg,MsgReceiver):
				self.listeners.append(msg)
			elif isinstance(msg,MsgIncoming):
				self._incoming(msg.msg)
			elif isinstance(msg,MsgReOpen):
				self._teardown()
			elif isinstance(msg,MsgError):
				self._error(msg.error)
			else:
				raise UnknownMessageType(msg)
			if not self.channel:
				self._setup()
			done = False

			for m in self.receivers:
				if m.blocking:
					break

			for mq in self.msgs:
				if done:
					break
				if self.max_open >= self.is_open:
					break
				while len(mq):
					m = mq.pop(0)
					r = m.send(self.channel):
					self.last_xmit = m
					self.last_xmit_at = now()
					if r is not None:
						if r:
							self.receivers.append(m)

					if m.blocking:
						done = True
						break
				
