#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
This code reads a config file.

	include NAME
		- read that file

"""

from homevent.statement import Statement, main_words
from homevent.module import Module
from homevent.check import Check,register_condition,unregister_condition
from homevent.parser import read_config
import os


class Include(Statement):
	name=("include",)
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
		return read_config(ctx,event[0])


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
