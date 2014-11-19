# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2012, Matthias Urlichs <matthias@urlichs.de>
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

from __future__ import division,absolute_import

from homevent import TESTING
from homevent.base import Name,SYS_PRIO,MIN_PRIO,MAX_PRIO
from homevent.worker import ConcurrentWorkSequence,ExcWorker
from homevent.collect import Collection
from homevent.context import Context
from homevent.twist import fix_exception

workers = {}

def register_worker(w):
	"""\
		Register a worker with a given priority.
		The only worker with priority zero is the system's (single)
		event logger.
		"""
	workers[w.id] = w
	
def unregister_worker(w):
	"""\
		Deregister a worker.
		"""
	del workers[w.id]

def list_workers(name=None):
	for w in workers.itervalues():
		if name is None or name == w.name:
			yield w

class Workers(Collection):
	name = "worker"
	def iteritems(self):
		for w in list_workers():
			yield w.id,w
	def __getitem__(self,k):
		if isinstance(k,Name):
			if len(k) != 1:
				raise SyntaxError,"Worker IDs are single numbers"
			k = k[0]
		return workers[int(k)]
Workers = Workers()

def collect_event(e):
	"""\
		Run an event through the system.
		Create a list of things to be done for this event.
		"""
	from homevent.logging import log_created

	work = ConcurrentWorkSequence(e,None)
	for w in workers.values():
		if w.does_event(e):
			w.match_count += 1
			work.append(w)
	log_created(work)
	return work

def collect_failure(e):
	"""\
		Run a failure through the system.
		Create a list of things to be done for it.
		"""
	from homevent.logging import log_created
	from homevent.event import Event
	assert isinstance(e,(Event,BaseException)),"Cannot be used as an event: "+repr(e)

	work = ConcurrentWorkSequence(e,None)
	for w in workers.values():
		if isinstance(w,ExcWorker) and w.does_failure(e):
			work.append(w)
	log_created(work)
	return work

def process_event(e, drop_errors=False):
	"""\
		Process an event. This is the procedure you'll be feeding
		externally-generated events to.
		"""
	#from homevent.logging import log_event,DEBUG,TRACE

	try:
		collect_event(e).process(event=e)
	except Exception:
		if not drop_errors:
			raise

def process_failure(e):
	"""\
		Process a failure event. This is the internal procedure that
		will mangle your errors.
		"""
	from homevent.logging import log_event,ERROR,log_exc
	log_event(event=e,level=ERROR)
	if getattr(e,"_did_event",False):
		if TESTING:
			raise RuntimeError("you called process_failure twice on "+str(e))
		return
	e._did_event = True
	try:
		collect_failure(e).process(event=e)
	except Exception as err:
		fix_exception(err)
		log_exc(msg="Error in failure handler", err=err, level=ERROR)
	
def run_event(event):
	try:
		process_event(event)
	except Exception as e:
		fix_exception(e)
		process_failure(e)
	
def simple_event(*args,**data):
	"""\
		A shortcut for triggering a "simple" background event
		"""
	from homevent.event import Event
	if isinstance(args[0],Context):
		if data:
			ctx = Context(args[0],**data)
		else:
			ctx = args[0]
		args = args[1:]
	else:
		ctx = Context(**data)
	run_event(Event(ctx, *args))

