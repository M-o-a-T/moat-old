# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2015 by Matthias Urlichs <matthias@urlichs.de>,
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
This module is the basis for processing FS20 datagrams.
"""

from __future__ import division,absolute_import

from moat.event import Event
from moat.run import simple_event
from moat.context import Context
from moat.fs20 import recv_handler,PREFIX, to_hc, handler_names
from moat import fs20 # for default_handler

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
