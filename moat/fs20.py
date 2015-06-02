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

import six

from moat.event import Event
from moat.run import simple_event
from moat.context import Context

from time import time

PREFIX_TIMESTAMP = 't'

PREFIX = {}

handlers = []
handler_names = {}
default_handler = None

@six.python_2_unicode_compatible
class WrongDatagram(TypeError):
	"""The datagram could not be recognized"""
	def __init__(self,data=None):
		self.data = data
	def __str__(self):
		r = "Bad FS20 datagram"
		if self.data is not None:
			r += " (%s)" % (repr(self.data),)
		return r

def to_hc(code, _len=8):
	"""convert a number to an n(=8)-digit 1234 value"""
	sft = 2*(_len-1)
	res = 0
	if isinstance(code,six.string_types):
		code = int(code)
	while True:
		res = 10*res + (((code >> sft) & 3) + 1)
		if not sft: break
		sft = sft-2
	return res

def from_hc(code, _len=8):
	"""convert a n(=8)-digit 1234 value to a number"""
	res = 0
	sft = 0
	if isinstance(code,six.string_types):
		code = int(code)
	assert len(str(code)) == _len, "wrong format: "+str(code)
	while code:
		c = code % 10
		assert c >= 1 and c <= 5, "wrong form: "+str(code)
		res += (c - 1) << sft
		sft += 2
		code = code // 10
	return res

def to_dev(code):
	"""convert a number to a four-digit 1234 value"""
	return to_hc(code, _len=4)
def from_dev(code):
	"""convert a four-digit 1234 value to a number"""
	return from_hc(code, _len=4)
		
def register_handler(h):
	global default_handler
	if h in handlers:
		raise RuntimeError("Handler already registered: %s" % (h,))
	handlers.append(h)
	handler_names[h.name] = h
	if default_handler is None:
		default_handler = h

def unregister_handler(h):
	global default_handler
	handlers.remove(h)
	del handler_names[h.name]
	if default_handler is h:
		try:
			default_handler = handlers[0]
		except IndexError:
			default_handler = None

class handler(object):
	"""\
	This abstract class defines the interface used to send and receive
	FS20-and-related datagrams. 
	"""
	def __init__(self,ctx=Context,**k):
		super(handler,self).__init__(**k)
		self.last_timestamp = None
		self.ctx = ctx()
	
	def send(self, prefix, data):
		"""\
		Send this datagram.
		"""
		raise NotImplementedError("Dunno how to send datagrams")

	def datagramReceived(self, prefix, data, handler=None, timestamp=None):
		try:
			ext = PREFIX[prefix]
		except KeyError:
			simple_event("fs20","unknown","prefix",prefix=prefix,data=data)
		else:
			return ext.datagramReceived(self.ctx, data, handler, timestamp)

class recv_handler(object):
	"""Common handling for incoming datagrams"""
	last_timestamp = None
	last_data = None

	def dataReceived(self, ctx, data, handler=None, timedelta=None):
		raise NotImplementedError("You need to override 'dataReceived'!")

	def datagramReceived(self, ctx, data, handler=None, timestamp=None):
		if timestamp is None:
			timestamp = time()
		if self.last_data is None or self.last_data != data:
			delta = None
			self.last_data = data
			self.last_timestamp = timestamp
		else:
			if self.last_timestamp:
				delta = timestamp - self.last_timestamp
			else:
				delta = None
		self.last_timestamp = timestamp

		return self.dataReceived(ctx, data, handler, delta)

