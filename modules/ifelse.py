# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2008, Matthias Urlichs <matthias@urlichs.de>
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
We need code for conditionals.

test foo bar:
	true if state on what ever
	false

if test foo bar:
	do-something
else:
	do-something-else

on what ever:
	if test foo bar

This code implements the "if" command.
"""

from homevent.statement import MainStatementList, main_words,global_words
from homevent.module import Module
from homevent.check import check_condition
from homevent.event import TrySomethingElse

from twisted.internet.defer import inlineCallbacks, returnValue

class IfStatement(MainStatementList):
	name=("if",)
	doc="Test if a condition holds"
	long_doc="""\
The "if" statement executes a block only if a condition is met.

Syntax:
	if [not] condition[...]:
		statement
		...

"""
	in_sub = False
	displayname = None
	else_do = None

	def add_else(self,proc):
		if self.else_do is None:
			self.else_do = proc
		else:
			self.else_do.add_else(proc)
		
	@inlineCallbacks
	def run(self,ctx,**k):
		want=True

		event = self.params(ctx)
		w = event[:]

		if w[0] == "not":
			want=False
			w = w[1:]

		if self.procs is None:
			if (yield check_condition(ctx,*w)) == want:
				return
			else:
				raise TrySomethingElse(*w)

		if (yield check_condition(ctx,*w)) == want:
			returnValue(super(IfStatement,self).run(ctx,**k))
		elif self.else_do is not None:
			returnValue(self.else_do.run(ctx,**k))


class ElseStatement(MainStatementList):
	name=("else",)
	doc="Alternate code if a condition is not met"
	long_doc="""\
The "else" statement executes a block only if a previous condition is not met.

Syntax:
	if [not] condition[...]:
		statement
	else:
		statement
		...

Implementation restriction: can't be used at top level. (Wrap with 'block:'.)
"""
	immediate = True
	def run(self,ctx,**k):
		if self.immediate:
			self.immediate = False
			self.parent.procs[-1].add_else(self)
		else:
			return super(ElseStatement,self).run(ctx,**k)
	

class ElseIfStatement(ElseStatement,IfStatement):
	name=("else","if")
	doc="Alternate test if a condition is not met"
	long_doc="""\
The "else if" statement executes a block only if a previous condition is
not met.

Syntax:
	if [not] condition[...]:
		statement
	else if condition[...]:
		statement
		...

Implementation restriction: can't be used at top level. (Wrap with 'block:'.)
"""
	immediate = True
	pass # multiple inheritance does everything we need ☺



class IfElseModule(Module):
	"""\
		This module implements the "if ...:" command.
		"""

	info = "if / else / else if"

	def load(self):
		main_words.register_statement(IfStatement)
		main_words.register_statement(ElseStatement)
		main_words.register_statement(ElseIfStatement)
	
	def unload(self):
		main_words.unregister_statement(IfStatement)
		main_words.unregister_statement(ElseStatement)
		main_words.unregister_statement(ElseIfStatement)
	
init = IfElseModule

import warnings
warnings.filterwarnings('ignore', message="returnValue.*", category=DeprecationWarning, lineno=85)

