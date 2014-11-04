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
This code does some standard I/O handling.

"""

from homevent.run import process_failure

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

		for proc,a,k in cb.itervalues():
			proc(*a,**k)

	def connectionLost(self,reason):
		if self in conns:
			conns.remove(self)

	def write(self,data):
		"""Mimic a normal 'file' output"""
		#for d in data.rstrip("\n").split("\n"):
		#	self.sendLine(data)
		self.transport.write(data)


