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
This code does some standard I/O handling.

"""

conns = []
def dropConnections():
	for c in conns:
		c.loseConnection()

class Outputter(object):
	"""Wraps standard output behavior"""
	def __init__(self, *a,**k):
		super(Outputter,self).__init__(*a,**k)
		self._drop_callbacks = {}
		self._callback_id = 0

	def addDropCallback(self,proc,*a,**k):
		self._callback_id += 1
		self._drop_callbacks[self._callback_id] = (proc,a,k)
		return self._callback_id

	def delDropCallback(self,id):
		del self._drop_callbacks[id]
	
	def connectionMade(self):
		super(Outputter,self).connectionMade()
		conns.append(self)

	def loseConnection(self):
		try:
			lc = super(Outputter,self).loseConnection
		except AttributeError:
			if self.transport:
				self.transport.loseConnection()
		else:
			lc()

		cb = self._drop_callbacks
		self._drop_callbacks = {}

		for proc,a,k in cb.values():
			proc(*a,**k)

	def connectionLost(self,reason):
		if self in conns:
			conns.remove(self)

	def write(self,data):
		"""Mimic a normal 'file' output"""
		#for d in data.rstrip("\n").split("\n"):
		#	self.sendLine(data)
		self.transport.write(data)

