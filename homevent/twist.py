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
	This module used to hold Twisted support stuff.
	Nowadays it holds stuff that's used to replace Twisted.
	… among other grab-bag stuff.
	"""

from twisted.internet.abstract import FileDescriptor
from twisted.internet import fdesc,defer,reactor,base
from twisted.python import log

from homevent.base import RaisedError
from homevent.geventreactor import DelayedCall,deferToGreenlet

import gevent
from gevent.event import AsyncResult

from posix import write
import sys
import os
import fcntl
import datetime as dt
import traceback

# This test is also in homevent/__init__.py, for recursive-import reasons
if "HOMEVENT_TEST" in os.environ:
	TESTING = True
else:
	TESTING = False

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
	

def fix_exception(e, tb=None):
	"""Add a __traceback__ attribute to an exception if it's not there already."""
	if not hasattr(e,"__traceback__"):
		if tb is None:
			tb = sys.exc_info()[2]
	if tb is not None:
		e.__traceback__ = tb

def print_exception(e=None,file=sys.stderr,backtrace=None):
	print >>file,format_exception(e,backtrace=backtrace)

def format_exception(e=None,backtrace=None):
	tb = getattr(e,"__traceback__",None)
	if backtrace is None:
		backtrace = not getattr(e,"no_backtrace",False)
	if tb is not None and backtrace:
		return "".join(traceback.format_exception(e.__class__, e, e.__traceback__))
	else:
		return unicode(e)


def reraise(e):
	"""Re-raise an exception, with its original traceback"""
	tb = getattr(e,"__traceback__",None)
	if tb is None:
		try:
			raise e
		except BaseException as e:
			tb = sys.exc_info()[2]
	else:
		del e.__traceback__
	raise e.__class__,e,tb

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


if "HOMEVENT_TEST" in os.environ:
	# Log all threads, wait for them to exit.
	gthreads = {}
	gjob=0
	gspawn = gevent.spawn
	def _completer(g,job):
		def pr_ok(v):
			print >>sys.stderr,"G RES %d %s" % (job,v)
		def pr_err(v):
			print >>sys.stderr,"G ERR %d %s" % (job,v)
		def pr_del(v):
			del gthreads[job]
#		g.link_value(pr_ok)
#		g.link_exception(pr_err)
		g.link(pr_del)
	def do_spawn(func,*a,**k):
		global gjob
		gjob += 1
		job = gjob
#		print >>sys.stderr,"G SPAWN %d %s %s %s" % (job,func,a,k)
		g = gspawn(func,*a,**k)
		gthreads[job]=(g,func,a,k)
		_completer(g,job)
		return g

	import gevent.greenlet as ggr
	gevent.spawn = do_spawn
	ggr.Greenlet.spawn = do_spawn
	Loggers = None

	def nr_threads(ignore_loggers=False):
		n = len(gthreads)
		if ignore_loggers:
			n -= len(Loggers.storage)
		if n < 0:
			n = 0
		return n
		
	def wait_for_all_threads():
		global Loggers
		from logging import Loggers as _Loggers
		from logging import stop_loggers
		Loggers = _Loggers

		n=0
#		for job,t in gthreads.iteritems():
#			print >>sys.stderr,"G WAIT %d %s %s %s" % ((job,)+t[1:])
	
		for r in (True,False):
			while nr_threads(r):
				if n==100000:
					for job,t in gthreads.iteritems():
						print >>sys.stderr,"G WAIT %d %s %s %s" % ((job,)+t[1:])
						t[0].kill()
	
					n=0
				n += 1
				try:
					gevent.sleep(0)
				except gevent.GreenletExit as ex:
#					fix_exception(ex)
#					print_exception(ex)
					pass
			if r:
				stop_loggers()
		for n in range(100):
			try:
				gevent.sleep(0)
			except gevent.GreenletExit as ex:
#				fix_exception(ex)
#				print_exception(ex)
				pass

else:
	def wait_for_all_threads():
		from logging import stop_loggers
		n = 2*kill_loggers()+10
		while n:
			n -= 1
			try:
				gevent.sleep(0)
			except gevent.GreenletExit:
				pass

gwait = 0
_log = None
TRACE = None
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
		global TRACE
		if _log is None:
			from homevent.logging import log as xlog, TRACE as xTRACE
			_log = xlog
			TRACE = xTRACE
		_log(TRACE,"+WAIT", self.w, *self.a)
		return self
	def __exit__(self, a,b,c):
		_log(TRACE,"-WAIT", self.w, *self.a)
		return False


### Safely start gevent threads

class _starting(object):
	pass

class Jobber(object):
	def start_job(self,attr, proc,*a,**k):
		with log_wait("start",attr,str(self)):
			while True:
				j = getattr(self,attr,None)
				if j is None:
					break
				elif j is _starting or not j.dead:
					return
				else:
					gevent.sleep(0.1)

		setattr(self,attr,_starting)
		j = gevent.spawn(proc,*a,**k)

		def err(e):
			try:
				e = e.get()
			except BaseException as e:
				pass
			from homevent.run import process_failure
			fix_exception(e)
			process_failure(e)

		def dead(e):
			if getattr(self,attr,None) is j:
				setattr(self,attr,None)

		j.link_exception(err)
		j.link(dead)
		setattr(self,attr,j)

	def stop_job(self,attr):
		j = getattr(self,attr,None)
		if j is None:
			return
		with log_wait("kill",attr,str(self)):
			if j is not _starting:
				j.kill()
			while getattr(self,attr,None) is j:
				gevent.sleep(0)

		
# avoids a warning from threading module on shutdown
sys.modules['dummy_threading'] = None

