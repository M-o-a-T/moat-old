# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2016 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
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
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

"""\
This part of the code controls the main loop.
"""

import sys
from moat.context import Context
from moat.event import Event
from moat.worker import Worker,ExcWorker
from moat.run import register_worker,unregister_worker, SYS_PRIO,MAX_PRIO,\
	process_event, process_failure
from moat.statement import Statement
from moat.io import dropConnections
from moat.twist import fix_exception,print_exception,\
	wait_for_all_threads
from moat.collect import Collection,Collected

import gevent
import aiogevent
import asyncio
import qbroker; qbroker.setup(gevent=True)
from qbroker.util.async import Main as _Main

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

		from moat.logging import stop_loggers
		stop_loggers()
		shut_down()

@asyncio.coroutine
def _async_stop_mainloop():
	j = gevent.spawn(_stop_mainloop)
	yield from aiogevent.wrap_greenlet(j)

## This should be in moat.collect, but import ordering problems make that impossible

class Shutdown_Collections(ExcWorker):
	"""\
		This worker kills off all open collections.
		"""
	prio = SYS_PRIO+2

	def does_event(self,ev):
		return (ev is shutdown_event)
	def process(self, event, **k):
		from moat.collect import collections
		super(Shutdown_Collections,self).process(**k)

		for w in sorted(collections.values(),key=lambda x:x.prio):
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
		super(MyMain,self).__init__(loop=qbroker.loop)

	@asyncio.coroutine
	def at_start(self):
		yield from super().at_start()
		start_up()
		if self.setup_proc:
			self.setup_proc()
		self.add_cleanup(_async_stop_mainloop)
		if self.main_proc:
			self.main_job = gevent.spawn(self.main_proc)
			self.add_cleanup(self.main_job.kill)

def mainloop(main=None,setup=None):
	global Main
	Main = MyMain(main,setup)
	Main.run()

