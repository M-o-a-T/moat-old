# -*- coding: utf-8 -*-

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
			raise SyntaxError("‹while ...› can only be used as a complex statement")

		event = self.params(ctx)
		w = event[:]

		if w[0] == "not":
			want=False
			w.pop(0)

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
			raise SyntaxError("‹repeat› can only be used as a complex statement")

		event = self.params(ctx)
		if len(event):
			raise SyntaxError("‹repeat› does not take arguments")

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
