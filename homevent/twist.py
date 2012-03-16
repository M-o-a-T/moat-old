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

from homevent.geventreactor import DelayedCall,deferToGreenlet

import gevent
from gevent.event import AsyncResult

from posix import write
import sys
import os
import fcntl
import datetime as dt
import traceback

tracked_errors = ("HOMEVENT_TRACK_ERRORS" in os.environ)

def track_errors(doit = None):
	global tracked_errors
	res = tracked_errors
	if doit is not None:
		tracked_errors = doit
	return res


# nonblocking versions of stdin/stdout

def setBlocking(flag,file):
	"""if @flag is true, the file descriptor will block upon reading."""
	if not hasattr(file,"fileno"):
		return

	# make stdin a (non-)blocking file
	fd = file.fileno()
	fl = fcntl.fcntl(fd, fcntl.F_GETFL)
	fcntl.fcntl(fd, fcntl.F_SETFL, (fl & ~os.O_NONBLOCK) if flag else (fl | os.O_NONBLOCK))

class StdInDescriptor(FileDescriptor):
	def fileno(self):
		return 0
	def doRead(self):
		try:
			setBlocking(False,0)
			return fdesc.readFromFD(0, self.dataReceived)
		finally:
			fdesc.setBlocking(True,0)

class StdOutDescriptor(FileDescriptor):
	def fileno(self):
		return 1
	def writeSomeData(self, data):
		try:
			setBlocking(False,1)
			return write(1,data)
		finally:
			setBlocking(True,1)
	
# Py3 stores an exception's traceback in a __traceback__ attribute.
# Do that too, instead of relying on Twisted's Failure wrapper.
def fix_exception(e, tb=None):
	"""Add a __traceback__ attribute to an exception if it's not there already"""
	if not hasattr(e,"__traceback__"):
		if tb is None:
			tb = sys.exc_info()[2]
		e.__traceback__ = tb

def print_exception(e=None,file=sys.stderr):
	traceback.print_exception(e.__class__, e, e.__traceback__, file=sys.stderr)

def format_exception(e=None,file=sys.stderr):
	return traceback.format_exception(e.__class__, e, e.__traceback__)

def reraise(e):
	"""Re-raise an exception, with its original traceback"""
	tb = getattr(e,"__traceback__",None)
	if tb is None:
		tb = sys.exc_info()[2]
	else:
		del e.__traceback__
	raise e.__class__,e,e.__traceback__


# count the number of active defer-to-later handlers
# so that we don't exit when one of them is still running,
# because that causes a deadlock.
#_running = 0
#_callme = None
#def call_when_idle(p):
#	global _callme
#	assert _callme is None, "Only one idle callback allowed"
#	_callme = p
#def _defer(d):
#	global _running
#	global _callme
#	d.callback(None)
#	_running -= 1
#	if _callme and not _running:
#		cm = _callme
#		_callme = None
#		cm()
#
# also, don't require an isInIOThread() test each time we want to defer something
# from some thread which may or may not be the main one:
# use this function instead
#def deferToLater(p,*a,**k):
#	global _running
#	_running += 1
#	d = defer.Deferred()
#	d.addCallback(lambda _: p(*a,**k))
#	if isInIOThread():
#		reactor.callLater(0,_defer,d)
#	else:
#		reactor.callFromThread(_defer,d)
#	reactor.wakeUp()
#	return d
deferToLater = deferToGreenlet


# When testing, we log the time an operation takes. Unfortunately, since
# the logged values are accurate up to 1/10th second, that means that
# the timestamp values in the logs will jitter merrily when something
# takes longer than 1/10th of a second. When the test runs for the first
# time (cold file system cache) or on a slower or busy machine, this is not
# at all uncommon.
#
# In addition, tests shouldn't take longer than necessary, so needless
# waiting is frowned upon.

# Thus, this code fakes timeouts by sorting stuff into bins and running
# these in-order, but it does not actually wait for anything unless the
# "force" flag is set, which denotes that the given timeout affects
# something "real" and therefore may not be ignored.

def sleepUntil(force,delta):
	from homevent.times import unixdelta,now

	if isinstance(delta,dt.datetime):
		delta = delta - now()
	if isinstance(delta,dt.timedelta):
		delta = unixdelta(delta)
	if delta < 0: # we're late
		delta = 0 # but let's hope not too late

	if "HOMEVENT_TEST" in os.environ:
		ev = AsyncResult()
		callLater(force,delta, ev.set,None)
		ev.get(block=True)
	else:
		sleep(delta)


def callLater(force,delta,p,*a,**k):
	from homevent.times import unixdelta,now

	if isinstance(delta,dt.datetime):
		delta = delta - now(force)
	if isinstance(delta,dt.timedelta):
		delta = unixdelta(delta)
	if delta < 0: # we're late
		delta = 0 # but let's hope not too late
	if "HOMEVENT_TEST" in os.environ:
		if force:
			cl = DelayedCall
			delta += reactor.realSeconds()
		else:
			from homevent.testreactor import FakeDelayedCall
			cl = FakeDelayedCall
			delta += reactor.seconds()
	else:
		cl = DelayedCall
		delta += reactor.seconds()
	cl = cl(reactor,delta, gevent.spawn,(p,)+a,k,seconds=reactor.seconds)

	return reactor.callLater(cl)


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

if False:
	gjob=0
	gspawn = gevent.spawn
	def _completer(g,job):
		def pr_ok(v):
			print >>sys.stderr,"G RES %d %s" % (job,v)
		def pr_err(v):
			print >>sys.stderr,"G ERR %d %s" % (job,v)
		g.link_value(pr_ok)
		g.link_exception(pr_err)
	def do_spawn(func,*a,**k):
		global gjob
		gjob += 1
		job = gjob
		print >>sys.stderr,"G SPAWN %d %s %s %s" % (job,func,a,k)
		g = gspawn(func,*a,**k)
		_completer(g,job)
		return g
	import gevent.greenlet as ggr
	gevent.spawn = do_spawn
	ggr.Greenlet.spawn = do_spawn

gwait = 0
_log = None
DEBUG = None
class log_wait(object):
	"""Usage:
		>>> with log_wait("foo","bar","baz"):
		...    do_something_blocking()
	"""

	def __init__(self,*a):
		global gwait
		gwait += 1
		self.a = a
		self.w = gwait

	def __enter__(self):
		global _log
		global DEBUG
		if _log is None:
			from homevent.logging import log as xlog, DEBUG as xDEBUG
			_log = xlog
			DEBUG = xDEBUG
		_log(DEBUG,"+WAIT", self.w, *self.a)
		return self
	def __exit__(self, a,b,c):
		_log(DEBUG,"-WAIT", self.w, *self.a)
		return False

# avoids a warning from threading module on shutdown
sys.modules['dummy_threading'] = None
#import threading as t
#def t_delete(self):
#    try:
#        with t._active_limbo_lock:
#            del t._active[t._get_ident()]
#    except KeyError:
#        if 'dummy_threading' not in sys.modules and 'greenlet' not in sys.modules:
#            raise
#t.Thread.__delete = t_delete
