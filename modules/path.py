# -*- coding: utf-8 -*-

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
