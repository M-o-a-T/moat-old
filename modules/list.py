# -*- coding: utf-8 -*-

"""\
This code represents a sample loadable module for homevent.

"""

from homevent.logging import log
from homevent.statement import Statement, global_words
from homevent.module import modules, ModuleDirs, Module
from homevent.run import list_workers


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
			print  >>self.ctx.out, " ".join(modules[event[0]].name),modules[event[0]].__doc__
		else:
			raise SyntaxError("Only one name allowed.")

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
		global_words.register_statement(ModList)
	
	def unload(self):
		global_words.unregister_statement(WorkerList)
		global_words.unregister_statement(ModList)
	
init = ListModule
