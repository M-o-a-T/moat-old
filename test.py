#!/usr/bin/python
# -*- coding: utf-8 -*-

from homevent.module import Loader,Unloader
from homevent.run import register_worker
from homevent.interpreter import InteractiveInterpreter
from homevent.parser import Parser
from homevent.statement import IgnoreStatement, main_words
from homevent.config import Load,Unload,WorkerList,ModList,LoadDir
from homevent.reactor import ShutdownHandler,mainloop,shut_down
from homevent.twist import StdInDescriptor
from homevent.module import load_module
from twisted.internet import reactor
from twisted.internet._posixstdio import StandardIO ## XXX unstable interface!
from twisted.internet.error import ConnectionDone
from homevent.context import Context
from homevent.handler import load as ht_load
from traceback import print_exc

register_worker(Loader())
register_worker(Unloader())

main_words.register_statement(Load)
main_words.register_statement(Unload)
main_words.register_statement(WorkerList)
main_words.register_statement(ModList)
main_words.register_statement(LoadDir)
main_words.register_statement(ShutdownHandler)
ht_load()
load_module("help")

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
def err(p,e):
	print >>p.out,e
	print_exc(file=p.out)

	return IgnoreStatement()
	
def ready():
	c=Context(errhandler=err)
	#c.logger=parse_logger
	i = InteractiveInterpreter(ctx=c)
	p = Parser(i, ctx=c)
	r = p.run(StdIO)
	r.addErrback(reporter)
	print """Ready. Type «help» if you don't know what to do."""

reactor.callLater(0.1,ready)
mainloop()

