# -*- coding: utf-8 -*-
"""\
	This module holds Twisted support stuff.
	"""

from twisted.internet.abstract import FileDescriptor
from twisted.internet import fdesc,defer,reactor,base
from twisted.python.threadable import isInIOThread

from posix import write
import sys

class StdInDescriptor(FileDescriptor):
	def fileno(self):
		return 0
	def doRead(self):
		try:
			fdesc.setNonBlocking(0)
			return fdesc.readFromFD(0, self.dataReceived)
		finally:
			fdesc.setBlocking(0)

class StdOutDescriptor(FileDescriptor):
	def fileno(self):
		return 1
	def writeSomeData(self, data):
		try:
			fdesc.setNonBlocking(1)
			return write(1,data)
		finally:
			fdesc.setBlocking(1)
	
def deferToLater(p,*a,**k):
	d = defer.Deferred()
	d.addCallback(lambda _: p(*a,**k))
	if isInIOThread():
		reactor.callLater(0,d.callback,None)
	else:
		reactor.callFromThread(d.callback,None)
	reactor.wakeUp()
	return d


# self.client.transport can be None
from twisted.conch.ssh import session,channel
def tlc(self):
	if self.client and self.client.transport:
		self.client.transport.loseConnection()
	channel.SSHChannel.loseConnection(self)
session.SSHSession.loseConnection = tlc


# Allow a Deferred to be initialized with another Deferred
def acb(self, result):
	if isinstance(result, defer.Deferred):
		result.addBoth(self.callback)
	else:
		self._startRunCallbacks(result)
defer.Deferred.callback = acb


# falls flat on its face without the test
def _cse(self, eventType):
	sysEvtTriggers = self._eventTriggers.get(eventType)
	if not sysEvtTriggers:
		return
	for callList in sysEvtTriggers[1], sysEvtTriggers[2]:
		for callable, args, kw in callList:
			try:
				callable(*args, **kw)
			except:
				log.deferr()
	# now that we've called all callbacks, no need to store
	# references to them anymore, in fact this can cause problems.
	del self._eventTriggers[eventType]
base.ReactorBase._continueSystemEvent = _cse

