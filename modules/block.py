# -*- coding: utf-8 -*-

"""\
This module contains statements to do simple statement aggregation.

"""

from homevent.module import Module
from homevent.logging import log
from homevent.statement import main_words, MainStatementList
from homevent.run import process_failure

class Block(MainStatementList):
	"""This just groups statements. For show, really — but also for testing."""
	name=("block",)
	doc="group multiple statements"
	# The MainStatementList run() already does everything we want

class Async(MainStatementList):
	"""This runs statements in the background."""
	name=("async",)
	doc="run multiple statements asynchronously"

	def run(self,*a,**k):
		d = super(Async,self).run(*a,**k)
		d.addErrback(process_failure)
		# note that d is *not* returned. This is intentional.

class BlockModule(Module):
	"""\
		This is a sample loadable module,
		plus some code you might want to reuse.
		"""

	info = "Block-level statements"

	def load(self):
		main_words.register_statement(Block)
		main_words.register_statement(Async)
	
	def unload(self):
		main_words.unregister_statement(Block)
		main_words.unregister_statement(Async)
	
init = BlockModule
