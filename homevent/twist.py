# -*- coding: utf-8 -*-
"""\
	This module holds Twisted support stuff.
	"""

from twisted.internet.abstract import FileDescriptor
from twisted.internet import fdesc,defer,reactor,base
from twisted.python import log,failure
from twisted.python.threadable import isInIOThread
from twisted.conch.ssh.session import SSHSessionProcessProtocol

from posix import write
import sys
import os
import datetime as dt

tracked_errors = ("HOMEVENT_TRACK_ERRORS" in os.environ)

def track_errors(doit = True):
	global tracked_errors
	tracked_errors = doit

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


# When testing, we log the time an operation takes. Unfortunately, since
# we're accurate up to 1/10th second, that means that the timestamp
# values in the logs will jitter merrily when they're near the
# 1/10th-second tick.

if "HOMEVENT_TEST" in os.environ:
	realLater = reactor.callLater
	def later(delta,proc,*a,**k):
		if delta > 0:
			nd = 0.1+2*delta
			d = dt.datetime.now()
			delta = nd - ((nd*1000000+d.microsecond)%100000)/1000000
		if delta < 0:
			delta = 0
		return realLater(delta,proc,*a,**k)
	reactor.callLater = later

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
			print >>sys.stderr,"-THR",tid," ".join(str(x) for x in _thr.keys())
			_syn.release()
	def cic(p,*a,**k):
		_syn.acquire()
		global _thr_id
		_thr_id += 1
		tid = _thr_id
		_syn.release()
		print >>sys.stderr,"+THR",tid,p,a,k
		return _cic(_tcall,tid,p,a,k)
	reactor.callInThread = cic

_ssw = SSHSessionProcessProtocol.write
def sws(self,data):
	if isinstance(data,unicode):
		data = data.encode("utf-8")
	return _ssw(self,data)
SSHSessionProcessProtocol.write = sws

fhw = FileDescriptor.write
def nfhw(self,data):
	if isinstance(data,unicode):
		data = data.encode("utf-8")
	return fhw(self,data)
FileDescriptor.write = nfhw


_fail = failure.Failure
class TwistFailure(_fail):
	def __init__(self, exc_value=None, exc_type=None, exc_tb=None):
		global tracked_errors
		if tracked_errors and exc_tb is None and exc_value is not None:
			try: raise exc_value
			except Exception: exc_tb = sys.exc_info()[2]
		_fail.__init__(self,exc_value,exc_type,exc_tb)
failure.Failure = TwistFailure
