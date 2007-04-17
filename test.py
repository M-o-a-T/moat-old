#!/usr/bin/python
# -*- coding: utf-8 -*-

from homevent.module import Loader,Unloader
from homevent.run import register_worker
from homevent.parser import parse, register_statement, Help
from homevent.config import Load,Unload,WorkerList,ModList
from homevent.reactor import ShutdownHandler,mainloop
from twisted.internet import reactor

register_worker(Loader())
register_worker(Unloader())

register_statement(Help())
register_statement(Load())
register_statement(Unload())
register_statement(WorkerList())
register_statement(ModList())
register_statement(ShutdownHandler())

def logger(*x):
	print " ".join((str(d) for d in x))

# TODO: create a line protocol for the parser and add stdin=>parser to this
def ready():
	print """Ready. Type «help» if you don't know what to do."""
reactor.callLater(0.1,ready)
mainloop()

