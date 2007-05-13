#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
This code does some standard I/O handling.

"""

from twisted.protocols.basic import LineReceiver
from twisted.internet import defer
from homevent.run import process_failure

_conns = []
def dropConnections():
	d = defer.succeed(None)
	def go_away(_,c):
		c.loseConnection()
	for c in _conns:
		d.addBoth(go_away,c)
	return d

class Outputter(object,LineReceiver): # "object" because L-R is old-style
	"""Wraps standard output behavior"""
	def __init__(self):
		super(Outputter,self).__init__()
		self._drop_callbacks = {}
		self._callback_id = 0

	def addDropCallback(self,proc,*a,**k):
		self._callback_id += 1
		self._drop_callbacks[self._callback_id] = (proc,a,k)
		return self._callback_id

	def delDropCallback(self,id):
		del self._drop_callbacks[id]
	
	def connectionMade(self):
		_conns.append(self)

	def loseConnection(self):
		cb = self._drop_callbacks
		self._drop_callbacks = {}
		d = defer.succeed(None)
		def call_it(_,proc,a,k):
			try:
				proc(*a,**k)
			except Exception:
				process_failure()
		for proc,a,k in cb.itervalues():
			d.addBoth(call_it,proc,a,k)
		return d

	def connectionLost(self,reason):
		if self in _conns:
			_conns.remove(self)
		q = self.queue
		if q is not None:
			q.put(None)

	def write(self,data):
		"""Mimic a normal 'file' output"""
		#for d in data.rstrip("\n").split("\n"):
		#	self.sendLine(data)
		self.transport.write(data)


