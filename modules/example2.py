# -*- coding: utf-8 -*-

"""\
This code represents a sample loadable module for homevent.

"""

from homevent.module import Module
from homevent.logging import log
from homevent.statement import main_words, MainStatementList

class Block(MainStatementList):
	"""This just groups statements. For show, really -- but also for testing."""
	name=("block",)
	doc="group multiple statements"

class ExampleModule(Module):
	"""\
		This is a sample loadable module,
		plus some code you might want to reuse.
		"""

	info = "yeah, test me baby"

	def __init__(self, name, *args):
		super(ExampleModule,self).__init__(name,*args)
	
	def load(self):
		main_words.register_statement(Block)
	
	def unload(self):
		main_words.unregister_statement(Block)
	
init = ExampleModule
