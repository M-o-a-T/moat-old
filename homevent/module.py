#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
This code processes module load/unload events.

"""

from twisted.python.reflect import namedAny
from twisted.python import failure
from twisted.internet import reactor,defer
from types import ModuleType
from homevent.worker import Worker
from homevent.event import Event
from homevent.run import process_event,process_failure
import sys
import os

ModuleDirs = []
def par(_): return os.path.join(os.pardir,_)
if os.path.exists("modules"):
	ModuleDirs.append("modules")
elif os.path.exists(par("modules")) and os.path.exists(par("Makefile")):
	ModuleDirs.append(par("modules"))

class ModuleExistsError(RuntimeError):
	"""A module with that name already exists."""
	pass

class Module(object):
	"""\
		This is a loadable module. See homevent.config.py, the
		"Loader" and "Unloader" classes, for examples.
		"""

	name = "Module"
	info = "some idiot programmer forgot to override me"

	def __init__(self, name, *args):
		"""\
			Initialize a module. The arguments are passed in from the 
			"load" command and may modify the module name, which needs
			to be unique.

			DO NOT register yourself in this code. That's the job of
			your load() function.

			Do not override the assignment (below) without good reason.
			"""
		self.name = (name,)+args
	
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
	

modules = {}

class Loader(Worker):
	"""Loads a module."""
	def __init__(self):
		super(Loader,self).__init__("Module Loader")

	def does_event(self,event):
		if len(event) < 3: return False
		if event[0] != "module": return False
		if event[1] != "load": return False
		return True

	def run(self,event, *a,**k):
		d = defer.Deferred()

		def doit(_):
			self.mod = None
			try:
				m = event[2:]
				if tuple(m) in modules:
					raise RuntimeError("This module already exists",event[2:])

				for d in ModuleDirs:
					p = os.path.join(d,*m)+".py"
					md = dict()
					try:
						c = compile(open(p,"r").read(), m[-1]+".py", "exec",0,True)
						eval(c,md)
					except OSError:
						continue

					mod = md["init"]
					if callable(mod):
						mod = mod(*m)
					elif len(event) > 3:
						raise RuntimeError("You cannot parameterize this module.")
					if mod.name in modules:
						raise RuntimeError("This module already exists(2)",mod.name)
					if not hasattr(mod,"load"):
						mod.load = md["load"]
						mod.unload = md["unload"]

					try:
						modules[m] = mod
						mod.load()
					except:
						del modules[m]
						raise

					self.mod = mod
					return True
			except Exception:
				exc = failure.Failure()
				exc.within = [event,self]
				process_failure(exc)
				return False

		def done(res):
			if res:
				return process_event(Event(event.ctx, "module","load-done",*self.mod.name), return_errors=True)

			if self.mod:
				try:
					self.mod.unload()
				except Exception:
					pass

			if self.mod is None or not hasattr(self.mod,"name"):
				name = event[2:]
			else:
				name = self.mod.name
			return process_event(Event(event.ctx, "module","load-fail",*name), return_errors=True)

#		def rx(_):
#			print "RX",_
#			return _
#		d.addCallback(rx)

		def do_start(_):
			return process_event(Event(event.ctx, "module","load-start",*event[2:]), return_errors=True)
		d.addCallback(do_start)
		d.addCallback(doit)
		d.addCallback(done)

		reactor.callLater(0,d.callback,None)
		return d
	

def unload_module(module):
	"""\
		Unloads a module.
		"""
	del modules[module.name]
	module.unload()

class Dummy(object): pass

class Unloader(Worker):
	"""Unloads a module."""
	def __init__(self):
		super(Unloader,self).__init__("Module Remover")

	def does_event(self,event):
		if len(event) < 3: return False
		if event[0] != "module": return False
		if event[1] != "unload": return False
		return True

	def run(self,event, *a,**k):
		d = defer.Deferred()
		sn = Dummy()

		def doit(_):
			sn.name = tuple(event[2:])
			sn.module = modules[sn.name]
			unload_module(sn.module)

		def done(_):
			return process_event(Event(event.ctx, "module","unload-done",*sn.module.name), return_errors=True)

		def notdone(exc):
			process_failure(exc)
			return process_event(Event(event.ctx, "module","unload-fail",*event[2:]), return_errors=True)

		def do_start(_):
			return process_event(Event(event.ctx, "module","unload-start",*event[2:]), return_errors=True)
		d.addCallback(do_start)
		d.addCallback(doit)
		d.addCallbacks(done, notdone)

		reactor.callLater(0,d.callback,None)
		return d
	
