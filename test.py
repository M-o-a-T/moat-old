#!/usr/bin/python
# -*- coding: utf-8 -*-

from homevent.interpreter import InteractiveInterpreter
from homevent.parser import parser_builder
from homevent.statement import main_words, global_words
from homevent.check import register_condition
from homevent.module import load_module, Load,Unload,LoadDir,ModuleExists
from homevent.reactor import ShutdownHandler,mainloop,shut_down
from twisted.internet import reactor
from twisted.internet._posixstdio import StandardIO ## XXX unstable interface!
from twisted.internet.error import ConnectionDone
from homevent.context import Context
from traceback import print_exc

global_words.register_statement(Load)
global_words.register_statement(Unload)
global_words.register_statement(LoadDir)
register_condition(ModuleExists)
main_words.register_statement(ShutdownHandler)
load_module("help")
load_module("list")

def parse_logger(t,*x):
	print t+":"+" ".join((repr(d) for d in x))

class StdIO(StandardIO):
	def connectionLost(self,reason):
		super(StdIO,self).connectionLost(self)
		if not reason.check(ConnectionDone):
			print "EOF:",reason
		shut_down()

def reporter(err):
	print "Error:",err
	
def ready():
	c=Context()
	#c.logger=parse_logger
	p = parser_builder(None, InteractiveInterpreter, ctx=c)()
	s = StdIO(p)
	r = p.parser.result
	r.addErrback(reporter)
	print """Ready. Type «help» if you don't know what to do."""

reactor.callLater(0.1,ready)
mainloop()

