# -*- coding: utf-8 -*-

"""\
This code represents a sample loadable module for homevent.

"""

from homevent.module import Module
from homevent.logging import log,DEBUG

class ExampleModule(Module):
	"""\
		This is a sample loadable module.
		"""

	info = "yeah, test me baby"

	def load(self):
		log(DEBUG,"Loading!")
	
	def unload(self):
		log(DEBUG,"Unloading!")
	
init = ExampleModule
