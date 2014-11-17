# -*- coding: utf-8 -*-

##
##  Copyright © 2008-2012, Matthias Urlichs <matthias@urlichs.de>
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
This module is the basis for processing FS20 datagrams.
"""

from __future__ import division,absolute_import

from homevent.event import Event
from homevent.run import simple_event
from homevent.context import Context
from homevent.fs20 import recv_handler,PREFIX, to_hc, handler_names
from homevent import fs20 # for default_handler

from time import time

PREFIX_FS20 = 'f'

groups = {}

class group(object):
	"""\
	This abstract class represents a group of FS20 devices.
	A group is defined by a common house code and checksum offset.
	"""

	handler = None

	def __init__(self, code, qsum):
		self.code = code
		self.qsum = qsum
		code = (code, qsum)
		if code in groups:
			raise RuntimeError("House code %04x/%02x already known" % code)
		groups[code] = self
	
	def delete(self,ctx=None):
		del groups[(self.code, self.qsum)]

	def datagramReceived(self, data, handler=None):
		raise NotImplementedError("Dunno how to process incoming datagrams")

	def send(self, data, handler=None):
		if handler is None:
			try:
				handler = handler_names[self.handler]
			except KeyError:
				handler = fs20.default_handler

			if handler is None:
				raise RuntimeError("No FS20 handler known")

		data = chr(self.code >> 8) + chr(self.code & 0xFF) + data
		qsum = self.qsum
		for c in data:
			qsum += ord(c)
		data += chr(qsum & 0xFF)

		return handler.send(PREFIX_FS20, data)


class fs20_handler(recv_handler):
	def dataReceived(self, ctx, data, handler=None, timedelta=None):
		if len(data) < 4:
			return # obviously way too short

		qs = 0
		for d in data:
			qs += ord(d)
		qs -= ord(data[-1]) # the above loop added it, that's nonsense
		qs = (ord(data[-1]) - qs) & 0xFF # we want the actual difference

		code = ord(data[0])*256+ord(data[1])
		try:
			g = groups[(code,qs)]
		except KeyError:
			simple_event("fs20","unknown","hc", hc=to_hc(code),checksum=qs,data=data)
			
		else:
			return g.datagramReceived(data[2:-1], handler, timedelta=timedelta)
PREFIX[PREFIX_FS20] = fs20_handler()
