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
This module contains statements to do simple statement aggregation.

"""

from homevent.module import Module
from homevent.logging import log
from homevent.statement import main_words, MainStatementList
from homevent.run import process_failure
from homevent.worker import HaltSequence
from homevent.twist import fix_exception,Jobber

import os
import gevent


class Block(MainStatementList):
	"""\
		This just groups statements. Necessary e.g. for top-level if:
	statements"""
	name="block"
	doc="group multiple statements"
	long_doc="""\
Group multiple statements. This is necessary for some commands (like else:)
which cannot be used on top level due to implementation restrictions.

	block:
		if foo:
			bar
		else:
			baz
"""
	pass # super.run() already does everything we want


class Async(MainStatementList,Jobber):
	"""This runs statements in the background."""
	name="async"
	doc="run multiple statements asynchronously"

	def _run(self,a,k):
		try:
			super(Async,self).run(*a,**k)
		except HaltSequence:
			pass
		except Exception as err:
			fix_exception(err)
			process_failure(err)

	def run(self,*a,**k):
		self.start_job("job", self._run,a,k)
		# TODO: some sort of global job list
		# so that they can be stopped when ending the program


class SkipThis(MainStatementList):
	"""This runs statements exactly never."""
	name="skip this"
	doc="do not run these statements"
	long_doc="""\
skip this:
	trigger foo
	# These statements need to be valid, but they're never excecuted.
"""

	def run(self,*a,**k):
		pass


class BlockModule(Module):
	"""\
		This module contains a couple of block-level statements.
		"""

	info = "Block-level statements"

	def load(self):
		main_words.register_statement(Block)
		main_words.register_statement(Async)
		main_words.register_statement(SkipThis)
	
	def unload(self):
		main_words.unregister_statement(Block)
		main_words.unregister_statement(Async)
		main_words.unregister_statement(SkipThis)
	
init = BlockModule
