# -*- coding: utf-8 -*-

##
##  Copyright (C) 2007  Matthias Urlichs <matthias@urlichs.de>
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
Around we go

repeat:
	wait for 1sec
	trigger Ping

while false:
	do-nothing

"""

from homevent.statement import MainStatementList, main_words,global_words
from homevent.module import Module
from homevent.check import check_condition
from twisted.internet import defer

class WhileStatement(MainStatementList):
	name=("while",)
	doc="while test: [statements]"
	long_doc="""\
The "while" statement executes a block over and over, as long as a
condition is met.

Syntax:
	while [not] condition[...]:
		statement
		...

"""

	def _loop(self,ctx, want=None,*w):
		d=defer.Deferred()

		def again(_=None):
			if want is not None and check_condition(ctx,*w) != want:
				d.callback(False)
				return
			e = super(WhileStatement,self).run(ctx)

			e.addCallback(again)
			def ex(_):
				d.errback(_)
			e.addErrback(ex)
		again()
		return d
		

	def run(self,ctx,**k):
		want = True
		if self.procs is None:
			raise SyntaxError(u"‹while ...› can only be used as a complex statement")

		event = self.params(ctx)
		w = event[:]

		if w[0] == "not":
			want=False
			w = w[1:]

		return self._loop(ctx,want,*w)



class RepeatStatement(WhileStatement):
	name=("repeat",)
	doc="repeat: [statements]"
	long_doc="""\
The "repeat" statement executes a block over and over.
It's basically an alias for "while true:".

Syntax:
	repeat
		statement
		...

"""
	def run(self,ctx,**k):
		if self.procs is None:
			raise SyntaxError(u"‹repeat› can only be used as a complex statement")

		event = self.params(ctx)
		if len(event):
			raise SyntaxError(u"‹repeat› does not take arguments")

		return self._loop(ctx)


class LoopModule(Module):
	"""\
		This module implements loops.
		"""

	info = "repeat: and while:"

	def load(self):
		main_words.register_statement(WhileStatement)
		main_words.register_statement(RepeatStatement)
	
	def unload(self):
		main_words.unregister_statement(WhileStatement)
		main_words.unregister_statement(RepeatStatement)
	
init = LoopModule
