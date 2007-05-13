#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
This code reads a config file.

Currently, it understands:

	help (see homevent.parser)

#	include NAME
#		- read that file too

	loaddir
		- list module directories
	loaddir "NAME"
		- add a module directory
	loaddir - "NAME"
		- drop a module directory

	load NAME
		- load the module/package homevent.NAME

	unload NAME
		- ... and remove it again.

	modlist
		- list the installed modules

	worklist
		- list the installed workers

#	config NAME:
#		foo bar baz
#		- pass these lines to this module's config() code
#		- see there for further documentation

Modules can register more words.
#Of particular interest are the switchboard and timer modules.

"""

from homevent.parser import Statement,Help
from homevent.run import process_event
from homevent.event import Event
from homevent.module import modules, ModuleDirs
import os

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

class LoadDir(Statement):
	name=("loaddir",)
	doc="list or change the module directory list"
	long_doc = """\
loaddir
	lists directories where "load" imports modules from
loaddir "NAME"
	adds the named directory to the end of the import list
loaddir + "NAME"
	adds the named directory to the beginning of the import list
loaddir - "NAME"
	removes the named directory from the import list
"""
	def input(self,wl):
		wl = wl[len(self.name):]
		if len(wl) == 0:
			for m in ModuleDirs:
				print >>self.ctx.out, m
			print >>self.ctx.out, "."
		else:
			w = wl[-1]
			if len(wl) == 1 and w not in ("+","-"):
				if not os.path.isdir(w):
					raise RuntimeError("«%s»: not found" % (w,))
				if wl[0] not in ModuleDirs:
					ModuleDirs.append(w)
				else:
					raise RuntimeError("«%s»: already listed" % (w,))
			elif len(wl) == 2 and wl[0] == "+":
				if not os.path.isdir(w):
					raise RuntimeError("«%s»: not found" % (w,))
				if wl[1] not in ModuleDirs:
					ModuleDirs.insert(0,w)
				else:
					raise RuntimeError("«%s»: already listed" % (w,))
			elif len(wl) == 2 and wl[0] == "-":
				try:
					ModuleDirs.remove(w)
				except ValueError:
					raise RuntimeError("«%s»: not listed" % (w,))
			else:
				raise SyntaxError("Usage: loaddir [ [ - ] name ]")


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

