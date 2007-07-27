#!/usr/bin/python
# -*- coding: utf-8 -*-

from homevent.interpreter import InteractiveInterpreter,Interpreter
from homevent.parser import parser_builder
from homevent.statement import main_words, global_words
from homevent.check import register_condition
from homevent.module import load_module, Load,Unload,LoadDir,ModuleExists
from homevent.reactor import ShutdownHandler,mainloop,shut_down
from twisted.internet import reactor,interfaces
from twisted.internet._posixstdio import StandardIO ## XXX unstable interface!
from twisted.internet.error import ConnectionDone,ConnectionLost
from homevent.context import Context
from traceback import print_exc
import os,sys

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
		if not reason.check(ConnectionDone,ConnectionLost):
			print "EOF:",reason

def reporter(err):
	print "Error:",err
	
def ready():
	if len(sys.argv) > 1 and sys.argv[1] == "P":
		# Log parser stuff
		from test import run_logger
		from homevent.logging import DEBUG
		logger = run_logger("testing_123",dot=False, level=DEBUG)
		c=Context(logger=logger.log)
	else:
		c=Context()
	#c.logger=parse_logger
	if os.isatty(0):
		i = InteractiveInterpreter
	else:
		i = Interpreter
	p = parser_builder(None, i, ctx=c)()
	s = StdIO(p)
	r = p.parser.result
	r.addErrback(reporter)
	r.addBoth(lambda _: shut_down())
	print """Ready. Type «help» if you don't know what to do."""

reactor.callLater(0.1,ready)
mainloop()

