# -*- coding: utf-8 -*-

##
##  Copyright © 2007, Matthias Urlichs <matthias@urlichs.de>
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

from __future__ import division

"""\
This part of the code defines what a (generic) worker is.

Briefly: a worker is something that recognizes an event and does
something about it.
"""

from homevent.context import Context
from homevent.event import Event,TrySomethingElse,NeverHappens
from homevent.base import Name,MIN_PRIO,MAX_PRIO
from homevent.twist import deferToLater, BaseFailure

from twisted.internet import defer
from twisted.internet.threads import deferToThread
from twisted.python import failure
from Queue import Queue,Empty
import os

class DropException:
	"""\
		A sentinel which log_end returns in order to not propagate exceptions beyond a Deferred's lifetime.
		"""
	pass

class HaltSequence(Exception):
	"""Do not execute the following workers."""
	pass
	

class WorkItem(object):
	u"""\
		One particular thing to do.

		*Everything* that this system does needs to be represented as a
		descendant of this class.

		This class itself is a dummy and does nothing, so you can use it
		to … well … do nothing.
		"""
	name = "No Work"
	prio = MIN_PRIO # not relevant here, but a required attribute

	def process(self,*a,**k):
		pass
	
	def report(self, verbose=False):
		yield "WORK: "+self.name

	def __repr__(self):
		return "<Item:%s>" % (self.name)

	def __str__(self):
		return repr(self)


seqnum = 0

class WorkSequence(WorkItem):
	"""\ 
		A WorkSequence encapsulates things that are to be done in
		sequence. It recognizes the fact that some work takes time
		and allows for logging events without executing them.

		'event' and 'worker' are the events which caused this sequence
		to be generated.
		"""
	in_step = None
	in_worker = None

	def __init__(self, event, worker):
		global seqnum
		seqnum += 1
		self.work = []
		self.event = event
		self.worker = worker
		if hasattr(event,"id"):
			self.id = self.event.id
		if hasattr(event,"ctx"):
			self.ctx = event.ctx()
		else:
			self.ctx = Context()
		self.iid = seqnum

		self.info = u"Worker %d for ‹%s›" % (self.iid,Name(self.event))

	def list(self):
		yield ("id",self.iid)
		yield ("event",Name(self.event))
		for l in self.report(99):
			yield ("report",l)

	def __repr__(self):
		if not hasattr(self,"work"):
			return "<%s:%d (?)>" % (self.__class__.__name__,self.iid)
		return "<%s:%d (%d)>" % (self.__class__.__name__, self.iid, len(self.work))
	
	def __str__(self):
		return repr(self)
	
	def append(self, w):
		if isinstance(w,SeqWorker):
			wn = w.process(event=self.event)
			if not isinstance(wn,WorkSequence):
				raise RuntimeError("%s: returned %s, not a WorkSequence" \
					% (w,wn))
			w = wn
		self.work.append(w)

	def process(self, *a,**k):
		r = deferToLater(self._process,*a,**k)
#		if "HOMEVENT_TEST" in os.environ:
#			r = deferToLater(self._process,*a,**k)
#		else:
#			r = deferToThread(self._process,*a,**k)
		return r

	handle_conditional = False

	@defer.inlineCallbacks
	def _process(self, *a,**k):
		assert self.work,"empty workqueue"
		self.in_step = step = 0
		self.in_worker = None
		res = None

		from homevent.logging import log_run,log_halted
		try:
			event = yield self.event
		except Exception:
			event = failure.Failure()
		skipping = False
		excepting = False
		if self.handle_conditional:
			DoRetry = TrySomethingElse
		else:
			DoRetry = NeverHappens

		for w in self.work:
			if w.prio >= MIN_PRIO and w.prio <= MAX_PRIO:
				step += 1
				if skipping:
					continue

			self.in_step = step
			self.in_worker = w
			r = None

			try:
				if not excepting or isinstance(w,ExcWorker):
					log_run(self,w,step)
#					d = w.process(event=self.event, queue=self)
#					if isinstance(d,defer.Deferred):
#						def repo(_):
#							print _
#							return _
#						d.addErrback(repo)
#					r = yield d
					r = yield w.process(event=self.event, queue=self)
			except HaltSequence:
				r = failure.Failure()
				log_halted(self,w,step)
				skipping = True
			except TrySomethingElse:
				pass
			except Exception:
				r = failure.Failure()
			else:
				if self.handle_conditional and w.prio >= MIN_PRIO:
					skipping = True

			if isinstance(r,BaseFailure):
				excepting = True
				if not hasattr(r,"within"):
					r.within=[w]
				r.within.append(self)
			if res is None:
				res = r
			elif isinstance(r,BaseFailure):
				from homevent.logging import log_exc
				log_exc("Unhandled nested exception", res)
				from homevent.run import process_failure
				yield process_failure(res)
				res = r

		defer.returnValue(res)

	def report(self, verbose=False):
		if not verbose:
			yield unicode(self) # +" for "+unicode(self.event)
			return

		if verbose > 2:
			v = verbose
		else:
			v = 1
		yield unicode(self)
		if self.work:
			prefix = "│  "
		else:
			prefix = "   "
		if hasattr(self.event,"report"):
			for r in self.event.report(False):
				yield prefix+r
		else:
			yield prefix+unicode(self.event)
		if self.worker:
			w="by "
			for r in self.worker.report(verbose):
				yield prefix+w+r
				w="   "

		pr = None
		step=1

		def pstep(a,b,c):
			if self.in_step and self.in_step == step:
				p_first = a+str(step)+"╕"
				p_mid = c+" "+u"│"
				p_last = c+" "+u"╵"
				p_single = a+" "+u"═"
				rep = pr.report(verbose-1)
			else:
				p_first = b+str(step)+u"╴"
				p_mid = c+"  "
				p_last = c+"  "
				p_single = b+str(step)+u"╴"
				rep = pr.report(v)
			rp=None

			pf=p_first
			pl=p_single
			for r in rep:
				if rp:
					yield pf+rp
					pf=p_mid
					pl=p_last
				rp=r
			if rp:
				yield pl+rp

		for w in self.work:
			if w.prio < MIN_PRIO or w.prio > MAX_PRIO+1: # Logger
				continue
			if pr:
				for _ in pstep("╞","├","│"): yield _
				step += 1
			pr = w
		for _ in pstep("╘","└"," "): yield _

class ConditionalWorkSequence(WorkSequence):
	"""\ 
		A WorkSequence which completes with the first step that does
		*not* raise an TrySomethingElse error.
		"""
	handle_conditional = True



def ConcurrentWorkSequence(WorkSequence):
	"""\
		A work sequence which does not wait for the previous step to complete.
		"""
	# TODO
	pass

class Worker(object):
	"""\
		This is a generic worker. It accepts an event and does things to it.
		"""
	prio = (MIN_PRIO+MAX_PRIO)//2
	def __init__(self, name):
		"""\
			Initialize this worker.
			
			You need to pass a hopefully-unique name (in addition to any
			other arguments your subclass needs).
			"""
		self.name = name
		self.id = 0

	def __repr__(self):
		if not hasattr(self,"name"):
			return "%s(<uninitialized>)" % (self.__class__.__name__,)
		return "%s(%s)" % \
			(self.__class__.__name__, repr(self.name))

	def __str__(self):
		return "=> %s:%s" % (self.__class__.__name__, self.name)
	def __unicode__(self):
		return u"⇒%s:%s" % (self.__class__.__name__, self.name)

	def report(self, verbose=False):
		yield "%s: %s" % \
			(self.__class__.__name__, self.name)
	
	def does_event(self, event):
		"""\
			Check if this worker can process that event.
			Do NOT actually do any work in this code!

			You need to override this.
			"""
		raise AssertionError("You need to override does_event()")
	
	def process(self, event,*a,**k):
		"""\
			Actually do the work on this event.

			You need to override this. Don't forget to set self.id, if
			appropriate.
			"""
		raise AssertionError("You need to override process()")
	

class SeqWorker(Worker):
	"""\
		This worker will return a WorkSequence.
		Its process() code MUST NOT have any side effects!
		"""
	pass


class ExcWorker(Worker):
	"""\
		This worker will handle failures.
		does_failure() will be checked for original failures only.
		"""

	def does_failure(self,event):
		return False
	pass


class DoNothingWorker(Worker):
	def __init__(self):
		super(DoNothingWorker,self).__init__("no-op")
	def does_event(self,event):
		return True
	def process(self, event, *a,**k):
		pass

