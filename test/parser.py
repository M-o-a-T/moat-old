#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
import homevent.parser as hp
from StringIO import StringIO
from test import run_logger

logger = run_logger("parser",dot=False)
log = logger.log

input = StringIO("""\

# call foo.input()
foo
# call foo.input("bar")
foo bar
# call foo.input("bar","baz")
foo bar baz
# call bar.input_block("baz","quux")
# which returns a SubBar object "subbar"
bar baz quux:
	# call WhatHandler(subbar).input("ever")
	what ever
	# call ForHandler(subbar).input_block("ever","and","ever")
	# which returns a SubFor object "subfor"
	for ever and ever:
		# call FoiledHandler(subfor).input("again")
		foiled again
	# call WhatHandler(subbar).input("else")
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
class FooHandler(hp.Statement):
	name="foo"
	doc="We foo around."
	def __repr__(self):
		return "‹"+self.__class__.__name__+"("+str(self.id)+")›"
	def __init__(self,*w):
		global _id
		_id += 1
		self.id = _id
		log("Init FooHandler: "+str(self.id)+" "+repr(w))
	def input(self,*w):
		log("Input FooHandler: "+repr(w))

class SubBar(object):
	def __repr__(self):
		return "‹"+self.__class__.__name__+"("+str(self.id)+")›"
	def __init__(self,*w):
		global _id
		_id += 1
		self.id = _id
		log("Init SubBar: "+str(self.id)+" "+repr(w))
	
class SubFor(object):
	def __repr__(self):
		return "‹"+self.__class__.__name__+"("+str(self.id)+")›"
	def __init__(self,*w):
		global _id
		_id += 1
		self.id = _id
		log("Init SubFor: "+str(self.id)+" "+repr(w))
	
class BarHandler(hp.StatementBlock):
	name="bar"
	doc="Have a bar, man!"
	def __repr__(self):
		return "‹"+self.__class__.__name__+"("+str(self.id)+")›"
	def __init__(self,*w):
		global _id
		_id += 1
		self.id = _id
		log("Init BarHandler: "+str(self.id)+" "+repr(w))
#	def __str__(self):
#		return "TheBar"
	def input_obj(self,*w):
		log("Create SubBar: "+repr(w))
		return SubBar(*w),
	
class ForHandler(hp.StatementBlock):
	name="for"
	doc="for you!"
	def __repr__(self):
		return "‹"+self.__class__.__name__+"("+str(self.id)+")›"
	def __init__(self,*w):
		global _id
		_id += 1
		self.id = _id
		log("Init ForHandler: "+str(self.id)+" "+repr(w))
#	def __str__(self):
#		return "ForThing"
	def input_obj(self,*w):
		log("Create SubFor: "+repr(w))
		return SubFor(*w),
	
class WhatHandler(hp.StatementBlock):
	name="what"
	doc="What is this?"
#	def __call__(self,a,b):
#		log("What gets called with "+a+" and "+b+"??")
	def __repr__(self):
		return "‹"+self.__class__.__name__+"("+str(self.id)+")›"
	def __init__(self,*w):
		global _id
		_id += 1
		self.id = _id
		log("Init WhatHandler: "+str(self.id)+" "+repr(w))
	def input(self,*w):
		log("Input WhatHandler:"+repr(w))

class FoiledHandler(hp.Statement):
	name="foiled"
	doc="not clingfilm"
#	def __call__(self,a,b):
#		log("Foiled by "+a+" and "+b+"!")
	def __repr__(self):
		return "‹"+self.__class__.__name__+"("+str(self.id)+")›"
	def __init__(self,*w):
		global _id
		_id += 1
		self.id = _id
		log("Init FoiledHandler: "+str(self.id)+" "+repr(w))
	def input(self,*w):
		log("Input FoiledHandler: "+repr(w))

foo=FooHandler()
bar=BarHandler()
what=WhatHandler()
foil=FoiledHandler()
for_=ForHandler()
BarHandler.register_statement(WhatHandler)
BarHandler.register_statement(ForHandler)
ForHandler.register_statement(FoiledHandler)
hp.register_statement(foo)
hp.register_statement(bar)
hp.register_statement(hp.Help(out=logger))

from tokenize import COMMENT
def logger(s,t,c,*x):
	if t == COMMENT:
		log(c.rstrip())


def main():
	d = hp.parse(input, logger=logger)
	d.addErrback(lambda _: _.printTraceback())
	d.addBoth(lambda _: h.shut_down())

h.mainloop(main)

