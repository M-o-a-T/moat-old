# -*- coding: utf-8 -*-
from __future__ import division

##
##  Copyright © 2007-2008, Matthias Urlichs <matthias@urlichs.de>
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
	This module holds Twisted support stuff.
	"""

from twisted.internet.abstract import FileDescriptor
from twisted.internet import fdesc,defer,reactor,base
from twisted.python import log,failure
from twisted.python.threadable import isInIOThread

from posix import write
import sys
import os
import datetime as dt

tracked_errors = ("HOMEVENT_TRACK_ERRORS" in os.environ)

def track_errors(doit = None):
	global tracked_errors
	res = tracked_errors
	if doit is not None:
		tracked_errors = doit
	return res


# nonblocking versions of stdin/stdout

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
	

# count the number of active defer-to-later handlers
# so that we don't exit when one of them is still running,
# because that causes a deadlock.
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

# also, don't require an isInIOThread() test each time we want to defer something
# from some thread which may or may not be the main one:
# use this function instead
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


# Simplification: sometimes we're late starting something.
# That is not a bug, that's life.
# reactor.callLater asserts >=0, so just make sure that it is.
wcl = reactor.callLater
def wake_later(t,p,*a,**k):
	if t < 0: t = 0

	r = wcl(t,p,*a,**k)

	# Bug workaround: Sometimes the Twisted reactor seems not to notice
	# that we just called reactor.callLater().
	if reactor.waker:
		reactor.waker.wakeUp()

	return r
reactor.callLater = wake_later



# When testing, we log the time an operation takes. Unfortunately, since
# the logged values are accurate up to 1/10th second, that means that
# the timestamp values in the logs will jitter merrily when something
# takes longer than 1/10th of a second, which is not at all difficult
# when the test runs for the first time.
#
# In addition, tests shouldn't take longer than necessary, so needless
# waiting is frowned upon.

# Thus, this code fakes timeouts by sorting stuff into bins and running
# these in-order, but it does not actually wait for anything unless the
# "force" flag is set, which denotes that the given timeout affects
# something "real" and therefore may not be ignored.

rcl = reactor.callLater
slot = None
GRAN = 20
def current_slot():
	if slot is None: return slot
	return slot/GRAN
	
if "HOMEVENT_TEST" in os.environ:
	import heapq
	slotid = 0
	slot = 0
	slots = []
	slotjobs = [{},{}]
	realslot = 0
	slot_running = False
	_real = None

	def _slot_run():
		global slot
		global realslot
		global slot_running
		if slot_running:
			#print >>sys.stderr,"DUP TRIGGER"
			return
		try:
			slot_running = True
			while slots:
				nx = slots[0]
				#print >>sys.stderr,"RUNNER now %d  do %d" % (slot,nx)

				nxjobs = slotjobs[False][nx]
				if not nxjobs:
					nxjobs = slotjobs[True][nx]
				if not nxjobs:
					#print >>sys.stderr,"RUNNER EMPTY %d" % (nx,)
					_nx = heapq.heappop(slots)
					assert nx == _nx
					del slotjobs[False][nx]
					del slotjobs[True][nx]
					continue
				job = nxjobs.pop(0)
				if job.dead:
					#print >>sys.stderr,"RUNNER SKIP %d %s" % (job.abs, job.proc)
					continue
				if job.force:
					#print >>sys.stderr,"RUNNER FORCE %d %s" % (job.abs, job.proc)
					nxjobs.insert(0,job) # should not happen often
					return
				if slot < nx: slot = nx
				job._run()

		except:
			log.deferr()
		finally:
			slot_running = False

	def reset_slots():
		global realslot
		realslot = slot
		return

	class CallLater(object):
		dead = False
		force = None
		q2 = False
		def _enqueue(self):
			if self.abs not in slotjobs[self.q2]:
				heapq.heappush(slots,self.abs)
				slotjobs[False][self.abs] = []
				slotjobs[True][self.abs] = []
			slotjobs[self.q2][self.abs].append(self)
			#print >>sys.stderr,"ADD %d %d: abs %d now %d  %s" % (id(self),self.q2,self.abs,slot,self.proc)
			if not slot_running:
				#print >>sys.stderr,"TRIGGER"
				rcl(0.01,_slot_run)
			#else:
				#print >>sys.stderr,"NO TRIGGER"
		
		def __repr__(self):
			return "<CL:"+repr(self.abs)+":"+repr(self.proc)+">"
			
		def __init__(self,force,delta,proc,*arg,**kwarg):
			global slot
			global slotid

			delta = int(delta * GRAN + 0.2)
			self.delta = delta
			self.abs = delta + slot
			self.proc = proc
			self.arg = arg
			self.kwarg = kwarg
			slotid += 1
			self.slotid = slotid
			if force and delta and self.abs > realslot:
				self.force = rcl((self.abs-realslot)/GRAN+0.01, self._run_force)
			elif force:
				self.q2 = True
			self._enqueue()
			
		def cancel(self):
			# take the cheap way out
			#print >>sys.stderr,"DEL",id(self),self.q2,self.delta,self.proc
			self.dead = True
			if self.force:
				self.force.cancel()
				self.force = False
				rcl(0.01,_slot_run)

		def _run_force(self):
			global realslot
			#print >>sys.stderr,"RUNNER CONTINUE %d %d %s" % (id(self), self.abs, self.proc)
			realslot = self.abs

			self.force = None
			rcl(0.01,_slot_run)
			
		def _run(self):
			if self.dead: return
			#print >>sys.stderr,"RUN",id(self),self.q2,self.abs,self.proc
			try:
				self.proc(*self.arg,**self.kwarg)
			except:
				log.deferr()

		def _die(self,info,*a,**k):
			from traceback import print_stack
			print >>sys.stderr,"OUCH",info,a,k
			print_stack(file=sys.stderr)
		def getTime(self,*a,**k): self._die("getTime",*a,**k)
		def reset(self,*a,**k): self._die("reset",*a,**k)
		def delay(self,*a,**k): self._die("delay",*a,**k)
		def activate_delay(self,*a,**k): self._die("activate_delay",*a,**k)
		def active(self,*a,**k): self._die("active",*a,**k)
		def __le__(self,*a,**k): self._die("__le__",*a,**k)

else:
	def reset_slots():
		pass

def callLater(force,delta,p,*a,**k):
	from homevent.times import unixdelta,now

	if isinstance(delta,dt.datetime):
		delta = delta - now()
	if isinstance(delta,dt.timedelta):
		delta = unixdelta(delta)
	if delta < 0: # we're late
		delta = 0 # but let's hope not too late
	if "HOMEVENT_TEST" in os.environ:
		return CallLater(force,delta,p,*a,**k)

	return rcl(delta,p,*a,**k)
def _callLater(delta,p,*a,**k):
	return callLater(2,delta,p,*a,**k)

if "HOMEVENT_TEST" in os.environ:
	reactor.callLater = _callLater


# Allow a Deferred to be called with another Deferred
# so that the result of the second is fed to the first
# (without checking for this case each time)
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

# Always encode Unicode strings in utf-8
fhw = FileDescriptor.write
def nfhw(self,data):
	if isinstance(data,unicode):
		data = data.encode("utf-8")
	return fhw(self,data)
FileDescriptor.write = nfhw

# Simplify failure handling
BaseFailure = failure.Failure
class TwistFailure(BaseFailure,BaseException):
	def __init__(self, exc_value=None, exc_type=None, exc_tb=None, captureVars=False):
		global tracked_errors
		try:
			a,b,c = sys.exc_info()
		except Exception:
			a,b,c = sys.exc_info()
		if exc_type is None: exc_type = a
		if exc_value is None: exc_value = b
		if exc_tb is None: exc_tb = c

		if exc_value is None:
			raise failure.NoCurrentExceptionError
		if not isinstance(exc_value,BaseException):
			exc_type = RuntimeError("Bad Exception: "+str(exc_value))
		BaseFailure.__init__(self,exc_value,exc_type,exc_tb,captureVars)

	def cleanFailure(self):
		"""Do not clean out the damn backtrace. We need it."""
		pass

failure.Failure = TwistFailure
