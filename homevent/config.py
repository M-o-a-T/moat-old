#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
This code reads a config file.

Currently, it understands:

	help (see homevent.parser)

	include NAME
		- read that file too

	load NAME
		- load the module/package homevent.NAME

	unload NAME
		- ... and remove it again.

	modules
		- list the installed modules

	config NAME:
		foo bar baz
		- pass these lines to this module's config() code
		- see there for further documentation

Modules can register more words. Of particular interest are the
switchboard and timer modules.

"""

from homevent.parser import Statement,Help
from homevent.run import process_event
from homevent.event import Event
from homevent.module import modules

class Load(Statement):
	name=("load",)
	doc="load a module"
	long_doc = """\
load NAME [args]...
	loads the named homevent module and calls its load() function.
	Emits an "module load NAME [args]" event.
"""
	def input(self,wl):
		process_event(Event(self.ctx, "module","load",*wl[len(self.name):]))

class Unload(Statement):
	name=("unload",)
	doc="unload a module"
	long_doc = """\
unload NAME [args]...
	unloads the named homevent module after calling its unload() function.
	Emits an "module unload NAME [args]" event.
"""
	def input(self,wl):
		process_event(Event(self.ctx, "module","unload",*wl[len(self.name):]))

class ModList(Statement):
	name=("modlist",)
	doc="list of modules"
	long_doc="""\
modlist
	shows a list of loaded modules.
modlist NAME [args...]
	shows the documentation string of that module.
	
"""
	def input(self,wl):
		wl = wl[len(self.name):]
		if not len(wl):
			for m in modules.itervalues():
				print >>self.ctx.out, " ".join(m.name)
			print >>self.ctx.out, "."
		elif len(wl) == 1:
			print  >>self.ctx.out, " ".join(modules[wl[0]].name),modules[wl[0]].__doc__
		else:
			raise SyntaxError("Only one name allowed.")

class WorkerList(Statement):
	name=("worklist",)
	doc="list of workers"
	long_doc="""\
worklist
	shows a list of available workers (code that reacts on events)
worklist NAME
	shows the documentation string of that worker.
"""
	def input(self,wl):
		wl = wl[len(self.name):]
		from homevent.run import list_workers
		if not wl:
			for w in list_workers():
				print >>self.ctx.out, w.prio,w.name
			print >>self.ctx.out, "."
		elif len(wl) == 1:
			for w in list_workers(wl[0]):
				print >>self.ctx.out, w.name,w.__doc__
			print >>self.ctx.out, "."
		else:
			raise SyntaxError("Too many parameters")
			return

