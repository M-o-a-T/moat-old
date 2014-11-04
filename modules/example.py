# -*- coding: utf-8 -*-

##
##  Copyright © 2007, Matthias Urlichs <matthias@urlichs.de>
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
This code represents a sample loadable module for homevent.

"""

from __future__ import division,absolute_import

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
