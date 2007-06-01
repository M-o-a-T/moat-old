# -*- coding: utf-8 -*-

"""\
This module contains statements to do simple statement aggregation.

"""

from homevent.module import Module
from homevent.logging import log
from homevent.statement import main_words, MainStatementList
from homevent.run import process_failure
from homevent.worker import HaltSequence

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
		def catch_halt(_):
			_.trap(HaltSequence)
			return None
		d.addErrback(catch_halt)
		d.addErrback(process_failure)
		# note that d is *not* returned. This is intentional.

class SkipThis(MainStatementList):
	"""This runs statements exactly never."""
	name=("skip","this")
	doc="do not run these statements"
	long_doc="""\
skip this:
	trigger foo
	# These statements need to be valid, but they're never excecuted.
"""

	def run(self,*a,**k):
		pass

class BlockModule(Module):
	"""\
		This is a sample loadable module,
		plus some code you might want to reuse.
		"""

	info = "Block-level statements"

	def load(self):
		main_words.register_statement(Block)
		main_words.register_statement(Async)
		main_words.register_statement(SkipThis)
	
	def unload(self):
		main_words.unregister_statement(Block)
		main_words.unregister_statement(Async)
		main_words.unregister_statement(SkipThis)
	
init = BlockModule
