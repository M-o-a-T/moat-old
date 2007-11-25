# -*- coding: utf-8 -*-

"""\
This part of the code controls the main loop.
"""

from twisted.internet import reactor,defer

from homevent.context import Context
from homevent.event import Event
from homevent.worker import Worker,ExcWorker,HaltSequence
from homevent.run import register_worker,unregister_worker, SYS_PRIO,MAX_PRIO,\
	process_event
from homevent.statement import Statement
from homevent.io import dropConnections
from homevent.twist import deferToLater,call_when_idle
from twisted.internet import reactor

__all__ = ("start_up","shut_down", "startup_event","shutdown_event",
	"ShutdownHandler","mainloop", "active_queues")

startup_event = Event(Context(), "startup")
shutdown_event = Event(Context(), "shutdown")

active_q_id = 0
active_queues = {}
running = False
stopping = False

class Shutdown_Worker_1(ExcWorker):
	"""\
		This worker counts event runs and makes sure that all are
		processed."""
	prio = SYS_PRIO+1

	def does_event(self,ev):
		return True
	def does_failure(self,ev):
		return True
	def process(self,queue,*a,**k):
		global active_q_id
		active_q_id += 1
		queue.aq_id = active_q_id
		active_queues[queue.aq_id] = queue
		if not running:
			raise HaltSequence("Not running. No new work is accepted!")
	def report(self,*a,**k):
		return ()

class Shutdown_Worker_2(ExcWorker):
	"""\
		This worker counts event runs and makes sure that all are
		processed."""
	prio = MAX_PRIO+3
	def does_event(self,ev):
		return True
	def does_failure(self,ev):
		return True
	def process(self,queue,*a,**k):
		del active_queues[queue.aq_id]
		del queue.aq_id
		if not running and not active_queues:
			stop_mainloop()
	def report(self,*a,**k):
		return ()

class Shutdown_Worker(Worker):
	"""\
		This worker does the actual shutdown.
		"""
	prio = MAX_PRIO+2
	def does_event(self,ev):
		return (ev is shutdown_event)
	def process(self,queue,*a,**k):
		return dropConnections()
	def report(self,*a,**k):
		yield "shutting down"

def start_up():
	"""\
		Code to be called first. The Twisted mainloop is NOT running.
		"""
	register_worker(Shutdown_Worker_1("shutdown first"))
	register_worker(Shutdown_Worker_2("shutdown last"))
	register_worker(Shutdown_Worker("shutdown handler"))

	global running
	if not running:
		running = True
		process_event(startup_event)
	
def _shut_down():
	"""\
		Code to be called last. The Twisted mainloop is running and will
		be stopped when all events have progressed.
		"""
	global running
	if running:
		process_event(shutdown_event)
		running = False

	if not active_queues:
		_stop_mainloop()

def shut_down():
	deferToLater(_shut_down)

def stop_mainloop():
	"""Sanely halt the Twisted mainloop."""
	deferToLater(_stop_mainloop)

def reactorstop():
	reactor.stop()

def _stop_mainloop():
	global stopping
	if not stopping:
		stopping = True
		dropConnections()
		call_when_idle(reactorstop)

class ShutdownHandler(Statement):
	"""A command handler to stop the whole thing."""
	name=("shutdown",)
	doc="stops executing the program."
	long_doc="""\
shutdown      stops executing the program.
shutdown now  ... but does not wait for active events to terminate.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event):
			if tuple(event) == ("now",):
				stop_mainloop()
				return
			raise ValueError(u"'shutdown' does not take arguments (except ‹now›).",event)
		shut_down()

def mainloop(main=None):
	if main:
		reactor.callWhenRunning(main)
	start_up()
	reactor.run()

