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
	def input(self,*wl):
		process_event(Event("module","load",*wl))

class Unload(Statement):
	name=("unload",)
	doc="unload a module"
	long_doc = """\
unload NAME [args]...
	unloads the named homevent module after calling its unload() function.
	Emits an "module unload NAME [args]" event.
"""
	def input(self,*wl):
		process_event(Event("module","unload",*wl))

class ModList(Statement):
	name=("modlist",)
	doc="list of modules"
	long_doc="""\
modlist
	shows a list of loaded modules.
modlist NAME [args...]
	shows the documentation string of that module.
	
"""
	def input(self,*wl):
		if wl:
			print  " ".join(modules[wl].name),modules[wl].__doc__
		else:
			for m in modules.itervalues():
				print " ".join(m.name)

class WorkerList(Statement):
	name=("worklist",)
	doc="list of workers"
	long_doc="""\
workerlist
	shows a list of available workers (code that reacts on events)
#workerlist NAME
#	shows the documentation string of that worker.
"""
	def input(self,*wl):
		from homevent.run import list_workers
		if not wl:
			for w in list_workers():
				print w.prio,w.name
		elif len(wl) == 1:
			for w in list_workers(wl[0]):
				print w.name,w.__doc__
		else:
			print "Too many parameters!"
			return

