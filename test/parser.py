#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
import homevent.parser as hp
from homevent.context import Context
from StringIO import StringIO
from test import run_logger

logger = run_logger("parser",dot=False)
log = logger.log

input = StringIO("""\

# call FooHandler(main).input("foo")
foo
# call FooHandler(main).input("foo","baz")
foo baz
# call FooHandler(main).input("foo","baz")
foo bar
# call BarHandler(main).input("foo","bar","baz")
foo bar baz
# call BarHandler(main).input_complex("baz","quux")
foo bar baz quux:
	# call WhatHandler(bar).input("ever")
	what ever
	# call ForHandler(bar).input_complex("ever","and","ever")
	for ever and ever:
		# call FoiledHandler(for).input("again")
		foiled again
	# call WhatHandler(bar).input("else")
	what else
# call FooHandler(main).input("foo","again")
foo again

# help
help
help help
# help foo => we foo around
help foo
# help foo baz: complains
help foo baz
# help foo bar => have a bar
help foo bar
# help bar for => for you
help foo bar for
# help foo bar for foiled => not clingfilm
help foo bar for foiled

#EOF
""")

_id=0
class sbr(object):
	def __repr__(self):
		return "‹%s (%d)›" % (super(sbr,self).__repr__()[1:-1], self.id)
	def __init__(self,parent=None,*a,**k):
		super(sbr,self).__init__(*a,**k)
		global _id
		_id += 1
		self.id = _id
		log("Init %s(%d) from %s" % (self.name,self.id, repr(parent)))
	def input(self,*w):
		log("Input %s(%d): %s" % (self.name,self.id,repr(w)))
	def input_complex(self,*w):
		log("InputComplex %s(%d): %s" % (self.name,self.id,repr(w)))

class FooHandler(sbr,hp.Statement):
	name=("foo",)
	doc="We foo around."

class BarHandler(sbr,hp.ComplexStatement):
	name=("foo","bar",)
	doc="Have a bar, man!"
	
class ForHandler(sbr,hp.ComplexStatement):
	name=("for",)
	doc="for you!"
	
class WhatHandler(sbr,hp.ComplexStatement):
	name=("what",)
	doc="What is this?"

class FoiledHandler(sbr,hp.Statement):
	name=("foiled",)
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

class TestInterpreter(hp.Interpreter):
    def complex_statement(self,args):
        fn = self.ctx.words.lookup(args)
        fn = fn(self.ctx)
        fn.input_complex(args)
        return TestInterpreter(ctx=self.ctx(words=fn))
	def done(self):
		log("... moving up")

class logwrite(object):
	def __init__(self,log):
		self.log = log
		self.buf = ""
	def write(self,data):
		self.buf += data
		if self.buf[-1] == "\n":
			if len(self.buf) > 1:
				for l in self.buf.rstrip("\n").split("\n"):
					self.log(l)
			self.buf=""

def main():
	d = hp.parse(input, TestInterpreter(Context(out=logwrite(log))), Context(logger=logger)) # , out=log)
	d.addErrback(lambda _: _.printTraceback())
	d.addBoth(lambda _: h.shut_down())

h.mainloop(main)

