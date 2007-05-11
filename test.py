#!/usr/bin/python
# -*- coding: utf-8 -*-

from homevent.module import Loader,Unloader
from homevent.run import register_worker
from homevent.parser import Parser, main_words, Help, Interpreter, IgnoreStatement
from homevent.config import Load,Unload,WorkerList,ModList
from homevent.reactor import ShutdownHandler,mainloop,stop_mainloop
from homevent.twist import StdInDescriptor
from twisted.internet import reactor
from twisted.internet._posixstdio import StandardIO ## XXX unstable interface!
from twisted.internet.error import ConnectionDone
from homevent.context import Context

register_worker(Loader())
register_worker(Unloader())

main_words.register_statement(Help)
main_words.register_statement(Load)
main_words.register_statement(Unload)
main_words.register_statement(WorkerList)
main_words.register_statement(ModList)
main_words.register_statement(ShutdownHandler)

def logger(t,*x):
	print t+":"+" ".join((repr(d) for d in x))

class StdIO(StandardIO):
	def connectionLost(self,reason):
		super(StdIO,self).connectionLost(self)
		if not reason.check(ConnectionDone):
			print "EOF:",reason
		stop_mainloop()
def reporter(err):
	print "Error:",err
def err(p,e):
	print >>p.out,e
	return IgnoreStatement()
	
def ready():
	c=Context(logger=logger, errhandler=err)
	i = Interpreter(ctx=c)
	p = Parser(i, ctx=c)
	r = p.run(StdIO)
	r.addErrback(reporter)
	print """Ready. Type «help» if you don't know what to do."""

reactor.callLater(0.1,ready)
mainloop()

