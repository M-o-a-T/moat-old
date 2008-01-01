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

"""\
This code implements access to collections.

"""

from homevent.logging import log
from homevent.statement import Statement, global_words
from homevent.module import modules, ModuleDirs, Module
from homevent.run import list_workers
from homevent.reactor import active_queues
from homevent.base import Name
from homevent.collect import collections


class List(Statement):
	name=("list",)
	doc="list of stuff"
	long_doc="""\
list
	shows all known collections
list coll
	shows a list of members of that collection
list coll NAME
	shows details for that collection member
	
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		n = len(event)
		if not n:
			for m in collections.itervalues():
				print >>self.ctx.out, " ".join(m.name)
		else:
			while n:
				try:
					coll = collections[Name(event[:n])]
					if n == len(event):
						for n,m in coll.iterkeys():
							m = m.info()
							if m is not None:
								print >>self.ctx.out,"%s :: %s" % (n,m)
							else:
								print >>self.ctx.out,"%s" % (n,)
					else:
						m = coll[Name(event[n:])]
						for s,t in m.list():
							print >>self.ctx.out,"%s: %s" % (s,t)
				except KeyError:
					n = n-1
				else:
					break
			if n==0:
				raise RuntimeError("I could not find a module for ‹›." % (Name(event),))

		print >>self.ctx.out, "."

class ModList(Statement):
	name=("list","module")
	doc="list of modules"
	long_doc="""\
list module
	shows a list of loaded modules.
list module NAME [args...]
	shows the documentation string of that module.
	
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			for m in modules.itervalues():
				print >>self.ctx.out, " ".join(m.name)
			print >>self.ctx.out, "."
		elif len(event) == 1:
			m = modules[Name(event)]
			print  >>self.ctx.out, " ".join(m.name),m.__doc__
		else:
			raise SyntaxError("Only one name allowed.")

class EventList(Statement):
	name=("list","event")
	doc="list of events that are currently processed"
	long_doc="""\
list event
	shows a list of running events.
list event ID
	shows details of that event.
	
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			for m in active_queues.itervalues():
				print >>self.ctx.out, m.aq_id,m.name
			print >>self.ctx.out, "."
		elif len(event) == 1:
			m = active_queues[event[0]]
			for r in m.report(99):
				print  >>self.ctx.out, r
		else:
			raise SyntaxError("Only one ID allowed.")

class WorkerList(Statement):
	name=("list","worker")
	doc="list of workers"
	long_doc="""\
list worker
	shows a list of available workers (code that reacts on events)
list worker NAME
	shows the documentation string of that worker.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if not len(event):
			for w in list_workers():
				print >>self.ctx.out, w.prio,w.name
			print >>self.ctx.out, "."
		elif len(event) == 1:
			for w in list_workers(event[0]): # should return only one
				print >>self.ctx.out, w.name,w.__doc__
			print >>self.ctx.out, "."
		else:
			raise SyntaxError("Too many parameters")
			return


class ListModule(Module):
	"""\
		This module provides a couple of common 'list FOO' functions.
		"""

	info = "provides a couple of common 'list FOO' functions"

	def load(self):
		global_words.register_statement(WorkerList)
		global_words.register_statement(EventList)
		global_words.register_statement(ModList)
		global_words.register_statement(List)
	
	def unload(self):
		global_words.unregister_statement(WorkerList)
		global_words.unregister_statement(EventList)
		global_words.unregister_statement(ModList)
		global_words.unregister_statement(List)
	
init = ListModule
