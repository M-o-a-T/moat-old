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
This part of the code controls the main loop.
"""

from __future__ import division,absolute_import

import sys
from homevent.context import Context
from homevent.event import Event
from homevent.worker import Worker,ExcWorker,HaltSequence
from homevent.run import register_worker,unregister_worker, SYS_PRIO,MAX_PRIO,\
	process_event, process_failure
from homevent.statement import Statement
from homevent.io import dropConnections
from homevent.twist import fix_exception,print_exception,\
	wait_for_all_threads
from homevent.collect import Collection,Collected

import gevent
from dabroker.util.thread import Main as _Main

__all__ = ("start_up","shut_down", "startup_event","shutdown_event",
	"ShutdownHandler","mainloop", "Events")

Main = None

startup_event = Event(Context(startup=True), "startup")
shutdown_event = Event(Context(shutdown=True), "shutdown")

active_q_id = 0
running = False
stopping = False

class Events(Collection):
    name = "event"
Events = Events()

class Shutdown_Worker(Worker):
	"""\
		This worker does the actual shutdown.
		"""
	prio = MAX_PRIO+2
	def does_event(self,ev):
		return (ev is shutdown_event)
	def process(self, **k):
		super(Shutdown_Worker,self).process(**k)
		dropConnections()
		_stop_mainloop()
	def report(self,*a,**k):
		yield "shutting down"

def start_up():
	"""\
		Code to be called first. The main loop is NOT running.
		"""
	register_worker(Shutdown_Worker("shutdown handler"))

	global running
	if not running:
		running = True
		try:
			process_event(startup_event)
		except Exception as e:
			fix_exception(e)
			process_failure(e)
	
def _shut_down():
	"""\
		Code to be called last. The main loop is running and will
		be stopped when all events have progressed.
		"""
	try:
		process_event(shutdown_event)
	except Exception as e:
		fix_exception(e)
		process_failure(e)

#	if not Events:
#		_stop_mainloop()

def shut_down():
	Main.stop()

def _stop_mainloop():
	global stopping
	if not stopping:
		stopping = True
		dropConnections()
		wait_for_all_threads() # Debugging

		from homevent.logging import stop_loggers
		stop_loggers()
		shut_down()



## This should be in homevent.collect, but import ordering problems make that impossible

class Shutdown_Collections(ExcWorker):
	"""\
		This worker kills off all open collections.
		"""
	prio = SYS_PRIO+2

	def does_event(self,ev):
		return (ev is shutdown_event)
	def process(self, event, **k):
		from homevent.collect import collections
		super(Shutdown_Collections,self).process(**k)

		def byprio(a,b):
			return cmp(a.prio,b.prio)
		for w in sorted(collections.itervalues(),cmp=byprio):
			if not w.can_do("del"):
				continue
			for d in w.values():
				try:
					d.delete(event.ctx)
				except Exception as ex:
					fix_exception(ex)
					print_exception(ex)
					# Logging may not work any more

	def report(self,*a,**k):
		return ()

register_worker(Shutdown_Collections("free all collections"))


class ShutdownHandler(Statement):
	"""A command handler to stop the whole thing."""
	name="shutdown"
	doc="stops executing the program."
	long_doc="""\
shutdown      stops executing the program.
shutdown now  ... but does not wait for active events to terminate.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			if tuple(event) == ("now",):
				_stop_mainloop()
				return
			raise ValueError(u"'shutdown' does not take arguments (except ‹now›).",event)
		shut_down()

class MyMain(_Main):
	def __init__(self, main=None, setup=None):
		self.main_proc = main
		self.setup_proc = setup
		self.main_job = None
		super(MyMain,self).__init__()
	def setup(self):
		start_up()
		if self.setup_proc:
			self.setup_proc()
	def main(self):
		if self.main_proc:
			self.main_job = gevent.spawn(self.main_proc)
			#self.register_stop(self.main_job.kill)
		self.shutting_down.wait()
	def cleanup(self):
		_stop_mainloop()

def mainloop(main=None,setup=None):
	global Main
	Main = MyMain(main,setup)
	Main.run()

