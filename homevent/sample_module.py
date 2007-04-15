# -*- coding: utf-8 -*-

"""\
This code represents a sample loadable module for homevent.

"""

from homevent.module import Module

class SampleModule(Module):
	"""\
		This is a sample loadable module.
		"""

	info = "yeah, test me baby"

	def __init__(self, name, *args):
		super(SampleModule,self).__init__(name,*args)
	
	def load(self):
		print "Loading!"
	
	def unload(self):
		print "Unloading!"
	
main = SampleModule
