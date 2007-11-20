# -*- coding: utf-8 -*-

"""\
This code does some standard I/O handling.

"""

from twisted.protocols.basic import LineReceiver
from twisted.internet import defer
from homevent.run import process_failure

conns = []
def dropConnections():
	d = defer.succeed(None)
	def go_away(_,c):
		c.loseConnection()
		return _
	for c in conns:
		d.addBoth(go_away,c)
	return d

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
		d = defer.succeed(None)
		def call_it(_,proc,a,k):
			try:
				proc(*a,**k)
			except Exception:
				process_failure()
		for proc,a,k in cb.itervalues():
			d.addBoth(call_it,proc,a,k)

	def connectionLost(self,reason):
		if self in conns:
			conns.remove(self)

	def write(self,data):
		"""Mimic a normal 'file' output"""
		#for d in data.rstrip("\n").split("\n"):
		#	self.sendLine(data)
		self.transport.write(data)


