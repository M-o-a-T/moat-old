# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2015 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
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
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

"""\
This code implements file existence checks.

"""

from moat.check import Check,register_condition,unregister_condition
from moat.module import Module
import os

class ExistsPathCheck(Check):
	name="exists path"
	doc="Check if there's something behind that path"
	def check(self,*args):
		assert len(args) == 1,"Need exactly one argument (file name)"
		return os.path.exists(args[0])

class ExistsFileCheck(Check):
	name="exists file"
	doc="Check if there's a file at that path"
	def check(self,*args):
		assert len(args) == 1,"Need exactly one argument (file name)"
		return os.path.isfile(args[0])

class ExistsDirCheck(Check):
	name="exists directory"
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
