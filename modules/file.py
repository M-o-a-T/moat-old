#!/usr/bin/python
# -*- coding: utf-8 -*-

"""\
This code reads a config file.

Currently, it understands:

	include NAME
		- read that file too

	load dir
		- list module directories
	load dir "NAME"
		- add a module directory
	load dir - "NAME"
		- remove a module directory

	load NAME
		- load the module/package homevent.NAME

	unload NAME
		- ... and remove it again.

#	config NAME:
#		foo bar baz
#		- pass these lines to this module's config() code
#		- see there for further documentation

Modules can register more words.
#Of particular interest are the switchboard and timer modules.

"""

from homevent.statement import Statement, main_words
from homevent.module import Module
from homevent.check import Check,register_condition,unregister_condition
from homevent.parser import read_config
import os


class FileExistsCheck(Check):
	name=("exists","file")
	doc="check if a handler exists"
	def check(self,*args):
		if len(args) != 1:
			raise SyntaxError("Usage: if exists file 'name'")
		return os.path.isfile(args[0])


class Include(Statement):
	name=("include",)
	doc="load a configuration file"
	long_doc = """\
include 'NAME'
	reads and processes the configuration file. The name probably needs
	to be quoted.
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
		register_condition(FileExistsCheck)
	
	def unload(self):
		main_words.unregister_statement(Include)
		unregister_condition(FileExistsCheck)
	
init = FileModule
