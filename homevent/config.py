#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
This code reads a config file.

Currently, it understands:

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

	list modules
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

from homevent.statement import Statement
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
	def run(self,ctx,**k):
		event = self.params(ctx)
		process_event(Event(self.ctx, "module","load",*event[len(self.name):]))

class Unload(Statement):
	name=("unload",)
	doc="unload a module"
	long_doc = """\
unload NAME [args]...
	unloads the named homevent module after calling its unload() function.
	Emits an "module unload NAME [args]" event.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		process_event(Event(self.ctx, "module","unload",*event[len(self.name):]))

class LoadDir(Statement):
	name=("load","dir")
	doc="list or change the module directory list"
	long_doc = """\
load dir
	lists directories where "load" imports modules from
load dir "NAME"
	adds the named directory to the end of the import list
load dir + "NAME"
	adds the named directory to the beginning of the import list
load dir - "NAME"
	removes the named directory from the import list
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		wl = event[len(self.name):]
		if len(wl) == 0:
			for m in ModuleDirs:
				print >>self.ctx.out, m
			print >>self.ctx.out, "."
		else:
			w = wl[-1]
			if len(wl) == 1 and w not in ("+","-"):
				if not os.path.isdir(w):
					raise RuntimeError("‹%s›: not found" % (w,))
				if wl[0] not in ModuleDirs:
					ModuleDirs.append(w)
				else:
					raise RuntimeError("‹%s›: already listed" % (w,))
			elif len(wl) == 2 and wl[0] == "+":
				if not os.path.isdir(w):
					raise RuntimeError("‹%s›: not found" % (w,))
				if wl[1] not in ModuleDirs:
					ModuleDirs.insert(0,w)
				else:
					raise RuntimeError("‹%s›: already listed" % (w,))
			elif len(wl) == 2 and wl[0] == "-":
				try:
					ModuleDirs.remove(w)
				except ValueError:
					raise RuntimeError("‹%s›: not listed" % (w,))
			else:
				raise SyntaxError("Usage: loaddir [ [ - ] name ]")

