# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
## This file is part of DaBroker, a distributed data access manager.
##
## DaBroker is Copyright © 2014 by Matthias Urlichs <matthias@urlichs.de>,
## it is licensed under the GPLv3. See the file `README.rst` for details,
## including optimistic statements by the author.
##
## This paragraph is auto-generated and may self-destruct at any time,
## courtesy of "make update". The original is in ‘utils/_boilerplate.py’.
## Thus, please do not remove the next line, or insert any blank lines.
##BP

"""\
	This code implements access to 1wire via the network.
	"""

import asyncio
import struct
from time import time
from dabroker.proto import Protocol, ProtocolInteraction

import logging
logger = logging.getLogger(__name__)

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

class OnewireProtocol(Protocol):
	MAX_LENGTH=10*1024
	def __init__(self):
		super().__init__()
		self.data = b""
		self.len = 24
		self.typ = None

	def received(self, data):
		self.data += data
		while len(self.data) >= self.len:
			if self.typ is None:
				assert self.len == 24
				version, payload_len, ret_value, format_flags, data_len, offset = struct.unpack('!6i', self.data[:24])
				self.data = self.data[24:]

				logger.debug("RECV %s %s %s %s %s x%x", version, payload_len, ret_value, format_flags, data_len, offset)
				if offset & 32768: offset = 0

				if version != 0:
					raise RuntimeError("Wrong version: %d" % version)
				if payload_len == -1 and data_len == 0 and offset == 0:
					logger.debug("RECV … server busy")
					continue # server busy

				if payload_len > self.MAX_LENGTH:
					raise RuntimeError("Length exceeded: %d %d %d"%(payload_len,offset,data_len))

				self.offset = offset
				if payload_len:
					self.data_len = data_len
				else:
					self.data_len = 0
				self.len = payload_len
				self.typ = ret_value
			else:
				# offset seems not to mean what we all think it means
				#data = self.data[self.offset:self.offset+self.data_len]
				data = self.data[:self.offset+self.data_len]
				logger.debug("RECV … %d %s",self.data_len,repr(data))
				self.data = self.data[self.len:]
				typ = self.typ

				self.typ = None
				self.len = 24

				yield (typ,data)

	def send(self, typ, data, rlen):
		"""Send an OWFS message to the other end of the connection."""
		flags = 0
		flags |= OWFlag.persist
		# needed for sometimes-broken 1wire daemons
		flags |= OWFlag.busret
		# flags |= 1<<8 ## ?
		flags |= OWtempformat.celsius << OWtempformat._offset
		flags |= OWdevformat.fdi << OWdevformat._offset

		logger.debug("SEND %d %d %d x%x %d %d %s", 0, len(data), typ, flags, rlen, 0, repr(data))
		self.transport.write(struct.pack("!6i", \
			0, len(data), typ, flags, rlen, 0) +data)

class OnewireInteraction(ProtocolInteraction):
	def __init__(self, *a,**kw):
		self._path = a
		super().__init__(**kw)

	def path(self,p):
		p = '/'+'/'.join(self._path+p)
		return p.encode('utf-8')+b'\0'

class OnewireDir(OnewireInteraction):
	@asyncio.coroutine
	def interact(self,*path):
		files = []
		self.send(OWMsg.dirall, self.path(path), 0)
		type,msg = yield from self.recv()
		assert type == 0
		for entry in msg.decode('utf-8').split(","):
			try: entry = entry[entry.rindex('/')+1:]
			except ValueError: pass
			entry = entry.rstrip("\0")
			files.append(entry)
		return files

class OnewireRead(OnewireInteraction):
	@asyncio.coroutine
	def interact(self,*path):
		self.send(OWMsg.get, self.path(path), 8192)
		res,msg = yield from self.recv()
		if res < 0:
			raise OnewireError(path,res)
		## TODO res vs. len(msg)?
		return msg.decode('utf-8')


class OnewireWrite(OnewireInteraction):
	@asyncio.coroutine
	def interact(self,*path, data=None):
		assert data is not None
		if not isinstance(data,bytes):
			data = str(data).encode('utf-8')
		self.send(OWMsg.get, self.path(path)+str(data).encode('utf-8'), len(data))
		res,msg = yield from self.recv()
		if res != len(data):
			raise OnewireError(path,res)


