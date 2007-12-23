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
This code implements primitive "if true" and "if false" checks.

"""

from homevent.check import Check,register_condition,unregister_condition
from homevent.module import Module
import os

class ExistsPathCheck(Check):
	name=("exists","path")
	doc="Check if there's something behind that path"
	def check(self,*args):
		assert len(args) == 1,"Need exactly one argument (file name)"
		return os.path.exists(args[0])

class ExistsFileCheck(Check):
	name=("exists","file")
	doc="Check if there's a file at that path"
	def check(self,*args):
		assert len(args) == 1,"Need exactly one argument (file name)"
		return os.path.isfile(args[0])

class ExistsDirCheck(Check):
	name=("exists","directory")
	doc="Check if there's a directory at that path"
	def check(self,*args):
		assert len(args) == 1,"Need exactly one argument (directory name)"
		return os.path.isdir(args[0])


class PathModule(Module):
	"""\
		This module provides a couple of filesystem existence checks.
		"""

	info = "Check for file/directory existence"

	def load(self):
		register_condition(ExistsPathCheck)
		register_condition(ExistsFileCheck)
		register_condition(ExistsDirCheck)
	
	def unload(self):
		unregister_condition(ExistsPathCheck)
		unregister_condition(ExistsFileCheck)
		unregister_condition(ExistsDirCheck)
	
init = PathModule
