# -*- coding: utf-8 -*-

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
This is the core of the event dispatcher.
"""

from homevent.base import Name,SYS_PRIO,MIN_PRIO,MAX_PRIO
from homevent.worker import WorkSequence,ConditionalWorkSequence,ExcWorker
from homevent.collect import Collection

from twisted.python import failure

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

class Workers(Collection):
	name = "worker"
	def iteritems(self):
		for w in list_workers():
			yield w.prio,w
	def __getitem__(self,k):
		raise SyntaxError("You cannot examine individual worker entries. Sorry.")
Workers = Workers()

def collect_event(e):
	"""\
		Run an event through the system.
		Create a list of things to be done for this event.
		"""
	from homevent.logging import log_created

	work = ConditionalWorkSequence(e,None)
	for wp in work_prios:
		for w in workers[wp]:
			if w.does_event(e):
				work.append(w)
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

def process_event(e, drop_errors=False):
	"""\
		Process an event. This is the procedure you'll be feeding
		externally-generated events to.
		"""
	from homevent.logging import log_event,DEBUG,TRACE

	log_event(e,level=DEBUG)
	d = collect_event(e).process()
#	def rv(_):
#		print "RVA",_
#		return _
#	d.addBoth(rv)
	if drop_errors:
		d.addErrback(lambda _: None)
	return d
	
def process_failure(e=None):
	"""\
		Process a failure event. This is the internal procedure that
		will mangle your errors.
		"""
	if e is None:
		e = failure.Failure()
	from homevent.logging import log_event,ERROR,log_exc
	log_event(e,level=ERROR)
	d = collect_failure(e).process()
	def err2(_):
		log_exc(msg="Error in failure handler", err=_, level=ERROR)
	d.addErrback(err2)
	return d
	
def simple_event(ctx, *args):
	"""
		A shortcut for triggering a "simple" background event
		"""
	from homevent.event import Event
	process_event(Event(ctx, *args)).addErrback(process_failure)

