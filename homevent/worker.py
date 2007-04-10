# *-* coding: utf-8 *-*

"""\
This part of the code defines what a (generic) worker is.

Briefly: a worker is something that recognizes an event and does
something about it.
"""

from homevent.event import Event, ExceptionEvent

from twisted.internet import defer
from twisted.python import failure

class WorkerError(AssertionError):
	"""\
		You tried to run a worker that's not been . That's stupid.
		"""
	pass

class WorkItem(object):
	"""\
		One particular thing to do.

		*Everything* that this system does needs to be represented as a
		descendant of this class.

		This class itself is a dummy and does nothing, so you can use it
		to … well … do nothing.
		"""
	name = "No Work"

	def run(self,*a,**k):
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
	def __init__(self, event, worker):
		global seqnum
		seqnum += 1
		self.work = []
		self.event = event
		self.worker = worker
		self.id = self.event.id
		self.iid = seqnum

	def __repr__(self):
		if not hasattr(self,"work"):
			return "<%s:%d (?)>" % (self.__class__.__name__,self.iid)
		return "<%s:%d (%d)>" % (self.__class__.__name__, self.iid, len(self.work))
	
	def __str__(self):
		return repr(self)
	
	def append(self, w):
		if isinstance(w,SeqWorker):
			wn = w.run(event=self.event)
			if not isinstance(wn,WorkSequence):
				raise RuntimeError("%s: returned %s, not a WorkSequence" \
					% (w,wn))
			w = wn
		self.work.append(w)

	def run(self, event=None,*a,**k):
		if not self.work:
			print "empty workqueue:",self.event
			return None

		from homevent.logging import log_run
		if event is None:
			event = self.event
		if not isinstance(event,defer.Deferred):
			event = defer.succeed(event)

		def do_std(r,step,w):
			try:
				log_run(self,w,r,step)
				res = w.run(res=r, event=self.event, queue=self)
			except Exception:
				res = ExceptionEvent(within=(self,w))
			else:
				if res is None:
					res = r
				if isinstance(res,failure.Failure) \
						and not isinstance(res, Event):
					res = ExceptionEvent(res.type,res.value,res.tb, \
						within=(self,w))
			return res

		step = 0
		from homevent.run import MIN_PRIO,MAX_PRIO
		for w in self.work:
			if not hasattr(w,"prio") or (w.prio >= MIN_PRIO and w.prio <= MAX_PRIO):
				step += 1
			if isinstance(w,ExcWorker):
				event.addBoth(do_std,step,w)
			else:
				event.addCallback(do_std,step,w)

		return event

	def report(self, verbose=False):
		if not verbose:
			yield str(self) # +" for "+str(self.event)
			return

		yield str(self)
		if self.work:
			prefix = "│  "
		else:
			prefix = "   "
		for r in self.event.report(verbose):
			yield prefix+r
		if self.worker:
			w="by "
			for r in self.worker.report(verbose):
				yield prefix+w+r
				w="   "

		pr = None
		step=1
		from homevent.run import MIN_PRIO,MAX_PRIO
		for w in self.work:
			if hasattr(w,"prio") and (w.prio < MIN_PRIO or w.prio > MAX_PRIO):
				continue
			if pr:
				prefix = "├"+str(step)+"╴"
				for r in pr.report(verbose-1):
					yield prefix+r
					prefix="│  "
				step += 1
			pr = w
		prefix = "└"+str(step)+"╴"
		for r in pr.report(verbose-1):
			yield prefix+r
			prefix="   "

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
		return "⇒%s:%s" % (self.__class__.__name__, self.name)

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
	
	def run(self, event,*a,**k):
		"""\
			Actually do the work on this event.

			You need to override this. Don't forget to set self.id, if
			appropriate.
			"""
		raise AssertionError("You need to override do_event()")
	

class SeqWorker(Worker):
	"""\
		This worker will return a WorkSequence.
		Its do_event() code MUST NOT have any side effects!
		"""
	pass

class ExcWorker(Worker):
	"""\
		This worker will accept exception events.
		"""
	pass

class DoNothingWorker(Worker):
	def __init__(self):
		super(DoNothingWorker,self).__init__("no-op")
	def does_event(self,event):
		return True
	def run(self, event):
		pass

