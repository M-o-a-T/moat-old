# -*- coding: utf-8 -*-

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

class IfStatement(MainStatementList):
	name=("if",)
	doc="if test: [statements]"
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
		
	def run(self,ctx,**k):
		want=True
		if self.procs is None:
			raise SyntaxError(u"‹if ...› can only be used as a complex statement")

		event = self.params(ctx)
		w = event[:]

		if w[0] == "not":
			want=False
			w.pop(0)

		if check_condition(ctx,*w) == want:
			return super(IfStatement,self).run(ctx,**k)
		elif self.else_do is not None:
			return self.else_do.run(ctx,**k)


class ElseStatement(MainStatementList):
	name=("else",)
	doc="else: [statements]"
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
	doc="else if: [statements]"
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
