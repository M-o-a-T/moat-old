# -*- coding: utf-8 -*-
"""\
	This module holds Twisted support stuff.
	"""

from twisted.internet.abstract import FileDescriptor
from twisted.internet import fdesc,defer,reactor,base
from twisted.python import log
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
	
_running = 0
_callme = None
def call_when_idle(p):
	global _callme
	assert _callme is None, "Only one idle callback allowed"
	_callme = p
def _defer(d):
	global _running
	global _callme
	d.callback(None)
	_running -= 1
	if _callme and not _running:
		cm = _callme
		_callme = None
		cm()


def deferToLater(p,*a,**k):
	global _running
	_running += 1
	d = defer.Deferred()
	d.addCallback(lambda _: p(*a,**k))
	if isInIOThread():
		reactor.callLater(0,_defer,d)
	else:
		reactor.callFromThread(_defer,d)
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


# hack callInThread to log what it's doing
if False:
	from threading import Lock
	_syn = Lock()
	_cic = reactor.callInThread
	_thr = {}
	_thr_id = 0
	def _tcall(tid,p,a,k):
		_thr[tid] = (p,a,k)
		try:
			return p(*a,**k)
		finally:
			_syn.acquire()
			del _thr[tid]
			print "-THR",tid,_thr
			_syn.release()
	def cic(p,*a,**k):
		_syn.acquire()
		global _thr_id
		_thr_id += 1
		tid = _thr_id
		_syn.release()
		print "+THR",tid,p,a,k
		return _cic(_tcall,tid,p,a,k)
	reactor.callInThread = cic
