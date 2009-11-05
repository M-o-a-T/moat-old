# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2008, Matthias Urlichs <matthias@urlichs.de>
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
This code implements module loading and unloading.

"""

from homevent.run import process_event
from homevent.statement import Statement
from homevent.event import Event
from homevent.check import Check
from homevent.base import Name
from homevent.collect import Collection,Collected

from twisted.python import failure
from twisted.internet.defer import inlineCallbacks,returnValue

import sys
import os

ModuleDirs = []
def par(_): return os.path.join(os.pardir,_)
#if os.path.exists("modules"):
#	ModuleDirs.append("modules")
#elif os.path.exists(par("modules")) and os.path.exists(par("Makefile")):
#	ModuleDirs.append(par("modules"))

class ModuleExistsError(RuntimeError):
	"""A module with that name already exists."""
	pass

class Modules(Collection):
	name = "module"
Modules = Modules()
Modules.does("del")

class Module(Collected):
	"""\
		This is a loadable module. See homevent.config.py, the
		"Loader" and "Unloader" classes, for examples.
		"""

	name = "Module"
	storage = Modules.storage
	info = "some idiot programmer forgot to override me"
	path = None

	def __init__(self, *name):
		"""\
			Initialize a module. The arguments are passed in from the 
			"load" command and may modify the module name, which needs
			to be unique.

			DO NOT register yourself in this code. That's the job of
			your load() function.

			Do not override the assignment (below) without good reason.
			"""
		assert len(name) > 0, "A module must be named!"
		super(Module,self).__init__(*name)
	
	def load(self):
		"""\
			Register the module with homevent.whatever. In particular,
			you may want to add configuration commands.

			This code needs to undo all of its effects if it raises an
			exception.
			"""
		raise NotImplementedError("This module does nothing.")
	
	def unload(self):
		"""\
			Unregister the module with homevent.whatever. You need to
			undo everything you did in .load(). Note that some
			deregistrations may fail!
			"""
		raise NotImplementedError("You need to undo whatever it is you did in load().")
	
	@inlineCallbacks
	def delete(self,ctx):
		yield process_event(Event(ctx, "module","unload",*self.name))
		yield self.unload()
		yield self.delete_done()

	def list(self):
		yield ("name",self.name)
		if self.path is not None:
			yield ("path",self.path)
		for l in self.info.split("\n"):
			yield ("info",l)
	
@inlineCallbacks
def load_module(*m):
	md = dict()
	mod = None
	p = None
	for d in ModuleDirs:
		p = os.path.join(d,m[-1])+".py"
		try:
			c = compile(open(p,"r").read(), p, "exec",0,True)
		except (OSError,IOError):
			md = None
			continue
		else:
			eval(c,md)
			break

	try:
		if not md:
			if "HOMEVENT_TEST" in os.environ:
				if os.path.isdir("modules"):
					p = "modules"
				else:
					p = os.path.join(os.pardir,"modules")
				p = os.path.join(p,m[-1])+".py"
				c = compile(open(p,"r").read(), p, "exec",0,True)
			else:
				from pkg_resources import resource_string
				p = "homevent.modules."+m[-1]+".py"
				c = compile(resource_string("homevent.modules", m[-1]+".py"), os.path.join('homevent','modules',m[-1]+".py"), "exec",0,True)
			eval(c,md)
	
		mod = md["init"]
		if callable(mod):
			mod = mod(*m)
		elif len(event) > 1:
			raise RuntimeError("You cannot parameterize this module.")
		if not hasattr(mod,"load"):
			mod.load = md["load"]
			mod.unload = md["unload"]
	
		try:
			yield mod.load()
		except BaseException,e:
			a,b,c = sys.exc_info()
			try:
				yield mod.unload()
			finally:
				raise a,b,c
		else:
			mod.path = p
	except BaseException:
		if mod is not None and hasattr(mod,"name") and mod.name in Modules:
			del Modules[mod.name]
		raise
	returnValue(mod)


class Load(Statement):
	name=("load",)
	doc="load a module"
	long_doc = """\
load NAME [args]...
	loads the named module and calls its load() function.
	Emits an "module load NAME [args]" event.
"""
	@inlineCallbacks
	def run(self,ctx,**k):
		event = self.params(ctx)
		yield load_module(*event)
		yield process_event(Event(self.ctx, "module","load",*event))


class LoadDir(Statement):
	name=("module","dir")
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
		if len(event) == 0:
			for m in ModuleDirs:
				print >>self.ctx.out, m
			print >>self.ctx.out, "."
		else:
			w = event[-1]
			if len(event) == 1 and w not in ("+","-"):
				if not os.path.isdir(w):
					raise RuntimeError(u"‹%s›: not found" % (w,))
				if event[0] not in ModuleDirs:
					ModuleDirs.append(w)
				else:
					raise RuntimeError(u"‹%s›: already listed" % (w,))
			elif len(event) == 2 and event[0] == "+":
				if not os.path.isdir(w):
					raise RuntimeError(u"‹%s›: not found" % (w,))
				if event[1] not in ModuleDirs:
					ModuleDirs.insert(0,w)
				else:
					raise RuntimeError(u"‹%s›: already listed" % (w,))
			elif len(event) == 2 and event[0] == "-":
				try:
					ModuleDirs.remove(w)
				except ValueError:
					raise RuntimeError(u"‹%s›: not listed" % (w,))
			else:
				raise SyntaxError("Usage: loaddir [ [ - ] name ]")

class ModuleExists(Check):
	name=("exists","module")
	doc="check if that module is loaded"
	def check(self,*args):
		assert args,"Need a module name (and optional parameters)"
		return Name(args) in Modules

