# *-* coding: utf-8 *-*

"""\
This part of the code controls the main loop.
"""

from twisted.internet import reactor,defer

from homevent.event import Event
from homevent.worker import ExcWorker
from homevent.run import register_worker,unregister_worker, SYS_PRIO,MAX_PRIO,\
	process_event

__all__ = ("start_up","shut_down", "startup_event","shutdown_event")

startup_event = Event("startup")
shutdown_event = Event("shutdown")

active_queues = []
running = False

class Shutdown_Worker_1(ExcWorker):
	"""\
		This worker counts event runs and makes sure that all are
		processed."""
	prio = SYS_PRIO+1

	def does_event(self,ev):
		return True
	def run(self,queue,*a,**k):
		if not running:
			raise RuntimeError("Not running. No new work is accepted!")
		active_queues.append(queue)
	def report(self,*a,**k):
		return ()

class Shutdown_Worker_2(ExcWorker):
	"""\
		This worker counts event runs and makes sure that all are
		processed."""
	prio = MAX_PRIO+1
	def does_event(self,ev):
		return True
	def run(self,queue,*a,**k):
		active_queues.remove(queue)
		if not running and not active_queues:
			reactor.stop()
	def report(self,*a,**k):
		return ()

def start_up():
	"""\
		Code to be called first. The Twisted mainloop is NOT running.
		"""
	register_worker(Shutdown_Worker_1("shutdown first"))
	register_worker(Shutdown_Worker_2("shutdown last"))

	global running
	running = True

	process_event(startup_event)
	
def shut_down():
	"""\
		Code to be called last. The Twisted mainloop is running and will
		be stopped when all events have progressed.
		"""
	process_event(shutdown_event)
	global running
	running = False

	if not active_queues:
		reactor.stop()


