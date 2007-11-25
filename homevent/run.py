# -*- coding: utf-8 -*-

"""\
This is the core of the event dispatcher.
"""

from twisted.python import failure
from homevent.constants import SYS_PRIO,MIN_PRIO,MAX_PRIO
from homevent.worker import WorkSequence,ExcWorker

workers = {}
work_prios = []

def register_worker(w):
	"""\
		Register a worker with a given priority.
		The only worker with priority zero is the system's (single)
		event logger.
		"""
	global work_prios

	if w.prio not in workers:
		workers[w.prio] = []
		work_prios = sorted(workers.keys())
	elif w.prio < MIN_PRIO or w.prio > MAX_PRIO:
		raise RuntimeError("More than one system worker (prio:%d) is registered!" % (w.prio,))
	workers[w.prio].append(w)
	
def unregister_worker(w):
	"""\
		Deregister a worker.
		"""
	global work_prios
	workers[w.prio].remove(w)
	if not workers[w.prio]: # last worker removed
		del workers[w.prio]
		work_prios = sorted(workers.keys())


def list_workers(name=None):
	for p in work_prios:
		for w in workers[p]:
			if name is None or name == w.name:
				yield w

def collect_event(e):
	"""\
		Run an event through the system.
		Create a list of things to be done for this event.
		"""
	from homevent.logging import log_created

	work = WorkSequence(e,None)
	for wp in work_prios:
		for w in workers[wp]:
			if w.does_event(e):
				work.append(w)
				break
	log_created(work)
	return work

def collect_failure(e):
	"""\
		Run a failure through the system.
		Create a list of things to be done for it.
		"""
	from homevent.logging import log_created

	work = WorkSequence(e,None)
	for wp in work_prios:
		for w in workers[wp]:
			if isinstance(w,ExcWorker) and w.does_failure(e):
				work.append(w)
	log_created(work)
	return work

def process_event(e, return_errors=False):
	"""\
		Process an event. This is the procedure you'll be feeding
		externally-generated events to.
		"""
	from homevent.logging import log_event,DEBUG
	if e[0] != "wait":
		log_event(e,level=DEBUG)
	d = collect_event(e).process()
#	def rv(_):
#		print "RVA",_
#		return _
#	d.addBoth(rv)
	if not return_errors:
		d.addErrback(lambda _: None)
	return d
	
def process_failure(e=None):
	"""\
		Process a failure event. This is the internal procedure that
		will mangle your errors.
		"""
	if e is None:
		e = failure.Failure()
	from homevent.logging import log_event,ERROR
	log_event(e,level=ERROR)
	d = collect_failure(e).process()
#	def rv(_):
#		print "RVB",_
#		return _
#	d.addBoth(rv)
	d.addErrback(lambda _: None)
	return d
	
