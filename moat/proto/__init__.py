# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2016 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
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
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

"""\
	This implements a bunch of mostly-generic protocol handling classes.
	"""
import asyncio
from time import time
import weakref
import sys

import logging
logger = logging.getLogger(__name__)

class Disconnected(BaseException):
	pass

class Protocol(asyncio.Protocol):
	"""\
		This class is responsible for translating the protocol's byte
		stream to messages, and vice versa.

		If you stream data out, you should periodically do
			await protocol.paused
		to make sure that the buffer doesn't go out of bounds.

		"""
	def __init__(self, loop=None):
		self._loop = loop if loop is not None else asyncio.get_event_loop()
		self.queue = asyncio.Queue(loop=self._loop)
		self.paused = asyncio.Future(loop=self._loop)
		self.paused.set_result(False)

	def close(self):
		self.transport.close()

	def connection_made(self, transport):
		#peername = transport.get_extra_info('peername')
		#print('Connection from {}'.format(peername))
		self.transport = transport

	def connection_lost(self, exc):
		if exc is None:
			exc = Disconnected()
		if not self.paused.done():
			self.paused.set_exception(exc) # pragma: no cover
		self.queue.put_nowait(exc)
		
	def data_received(self, data):
		try:
			for m in self.received(data):
				self.queue.put_nowait(m)
		except BaseException as exc:
			if not self.paused.done():
				self.paused.set_exception(exc)
			self.queue.put_nowait(exc)

	def received(self, data): # pragma: no cover
		"""\
			You must override this method!

			Translate the incoming byte stream to messages and yield them.
			"""
		raise NotImplementedError("You need to override %s.receive" % self.__class__.__name__)
	
	def send(self, whatever=None, *a,**k):
		"""\
			You must override this method!

			Translate the message to be sent to a bytestream
			and call self.transport.write().
			"""
		raise NotImplementedError("You need to override %s.send" % self.__class__.__name__)

	def pause_writing(self): # pragma: no cover
		self.paused = asyncio.Future(loop=self._loop)
	def resume_writing(self): # pragma: no cover
		self.paused.set_result(True)
		
class ProtocolInteraction(object):
	"""\
		A generic message read/write thing.

		You override interact() to send and receive messages.
		A client typically sends a message, waits for a reply (or more), possibly repeats, then exits.

		async def interact(self):
			await self.paused ## periodically do this if you send lots
			self.send("Foo!")
			assert (await self.recv()) == "Bar?"
			
		"""

	_conn = None

	def __init__(self, *, loop=None, conn=None):
		self._protocol = None
		self._loop = loop if loop is not None else asyncio.get_event_loop()
		if conn is not None:
			self._conn = weakref.ref(conn)

	@property
	def paused(self): # pragma: no cover
		return self._paused()
	async def _paused(self): # pragma: no cover
		p = self._protocol.paused
		if not p.done():
			await p
			self._protocol.paused.result()

	def run(self,*a, **kw):
		"""\
			If you submitted the connection while creating, you can run the interaction on this connection here.
			"""
		c = self._conn()
		if c is None:
			raise RuntimeError("Connection has gone away")
		return c.run(self,*a,**kw)
	run._is_coroutine = True

	async def interact(self,*a,**k): # pragma: no cover
		raise NotImplementedError("You need to override %s.interact" % self.__class__.__name__)

	def send(self,*a,**k):
		self._protocol.send(*a,**k)

	async def recv(self):
		res = await self._protocol.queue.get()
		if isinstance(res,BaseException):
			raise res
		return res
		
class ProtocolClient(object):
	"""\
		A generic streaming client.

		You use this object by encapsulating a sequence of read or write
		calls in a ProtocolInteraction, then call this object's "run"
		method with it.

		This client uses multiple connections.
		"""
	MAX_IDLE = 10
	def __init__(self, protocol, host,port, loop=None):
		"""\
			@protocol: factory for the protocol to run on the connection(s)
			@host, @port: the service to talk to.
			"""
		self.protocol = protocol
		self.host = host
		self.port = port
		self.conns = []
		self._loop = loop if loop is not None else asyncio.get_event_loop()
		self._id = 1
		self.tasks = {}

	async def _get_conn(self):
		now = time()
		while self.conns:
			ts,conn = self.conns.pop()
			if ts > now-self.MAX_IDLE:
				break
			assert conn.queue.empty()
			try:
				conn.close()
			except Exception: # pragma: no cover
				logger.exception("Closing idle connection")
		else:
			try:
				_,conn = await self._loop.create_connection(lambda: self.protocol(loop=self._loop), self.host,self.port)
			except Exception:
				logger.error("No connection to %s:%s", self.host,self.port)
				raise
		return conn
		
	def _put_conn(self,conn):
		self.conns.append((time(),conn))

	@property
	def next_id(self):
		id = self._id
		self._id += 1
		return id

	async def run(self, interaction, *a,**k):
		"""\
			Run the interaction on (an instance of) this connection.
			"""
		conn = await self._get_conn()
		f = None
		id = self.next_id
		try:
			if interaction._protocol is not None:
				raise RuntimeError("%s is running twice" % repr(interaction))
			try:
				interaction._protocol = conn
				f = asyncio.ensure_future(interaction.interact(*a,**k), loop=self._loop)
				self.tasks[id] = f
				await f
				res = f.result()
			finally:
				assert interaction._protocol is conn
				interaction._protocol = None
		except BaseException as exc:
			if f is not None and not f.done():
				f.set_Exception(exc)
			raise
		else:
			if f is not None and not f.done():
				f.set(True) # pragma: no cover
			self._put_conn(conn)
			conn = None
			return res
		finally:
			if f is not None and not f.done():
				f.set(False) # pragma: no cover
			self.tasks.pop(id,None)
			if conn is not None:
				conn.close()

	def abort(self):
		"""Kill all tasks and connections"""
		for id,f in self.tasks.items():
			try:
				f.cancel()
			except Exception: # pragma: no cover
				pass
		while self.conns:
			_,conn = self.conns.pop()
			try:
				conn.close()
			except Exception: # pragma: no cover
				logger.exception("Trying to abort")

	async def close(self):
		"""Wait for all tasks to finish"""
		while self.tasks:
			for k in list(self.tasks.keys()):
				await self.tasks.pop(k,None)
		self.abort()
