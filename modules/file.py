# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2012, Matthias Urlichs <matthias@urlichs.de>
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
This code reads a config file.

	include NAME
		- read that file

"""

from __future__ import division,absolute_import

from moat.statement import Statement, main_words
from moat.module import Module
from moat.check import Check,register_condition,unregister_condition
from moat.parser import parse
import os


class Include(Statement):
	name="include"
	doc="load a configuration file"
	long_doc = """\
include 'NAME'
	reads and processes the named configuration file.
	The name probably needs to be quoted.
"""
	def run(self,ctx,**k):
		event = self.params(ctx)
		if len(event) != 1:
			raise SyntaxError("Usage: include 'filename'")
		parse(event[0],ctx=ctx)


class FileModule(Module):
	"""\
		This module implements a few file-related functions.
		"""

	info = "Basic (include) file handling"

	def load(self):
		main_words.register_statement(Include)
	
	def unload(self):
		main_words.unregister_statement(Include)
	
init = FileModule
