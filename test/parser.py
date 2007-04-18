#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
import homevent.parser as hp
from StringIO import StringIO
from test import run_logger

logger = run_logger("parser",dot=False)
log = logger.log

input = StringIO("""\

# call FooHandler(main).input()
foo
# call FooHandler(main).input("bar")
foo bar
# call FooHandler(main).input("bar","baz")
foo bar baz
# call BarHandler(main).input_block("baz","quux")
bar baz quux:
	# call WhatHandler(bar).input("ever")
	what ever
	# call ForHandler(bar).input_block("ever","and","ever")
	for ever and ever:
		# call FoiledHandler(for).input("again")
		foiled again
	# call WhatHandler(bar).input("else")
	what else
foo again

# help
help
# help foo
help foo
# help bar
help bar
# help bar for
help bar for
# help bar for foiled
help bar for foiled

""")

_id=0
class sbr(object):
	def __repr__(self):
		return "‹%s (%d)›" % (super(sbr,self).__repr__()[1:-1], self.id)
	def __init__(self,parent,*w):
		global _id
		_id += 1
		self.id = _id
		log("Init %s(%d) from %s: %s" % (self.name,self.id, parent,repr(w)))
	def input(self,*w):
		log("Input %s(%d): %s" % (self.name,self.id,repr(w)))

class FooHandler(sbr,hp.Statement):
	name="foo"
	doc="We foo around."

class BarHandler(sbr,hp.StatementBlock):
	name="bar"
	doc="Have a bar, man!"
	
class ForHandler(sbr,hp.StatementBlock):
	name="for"
	doc="for you!"
	
class WhatHandler(sbr,hp.StatementBlock):
	name="what"
	doc="What is this?"

class FoiledHandler(sbr,hp.Statement):
	name="foiled"
	doc="not clingfilm"

BarHandler.register_statement(WhatHandler)
BarHandler.register_statement(ForHandler)
ForHandler.register_statement(FoiledHandler)
hp.main_words.register_statement(FooHandler)
hp.main_words.register_statement(BarHandler)
hp.main_words.register_statement(hp.Help)

from tokenize import COMMENT

def logger(s,t,c,*x):
	if t == COMMENT:
		log(c.rstrip())

def main():
	d = hp.parse(input, logger=logger, out=log)
	d.addErrback(lambda _: _.printTraceback())
	d.addBoth(lambda _: h.shut_down())

h.mainloop(main)

