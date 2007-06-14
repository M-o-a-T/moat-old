#!/usr/bin/python
# -*- coding: utf-8 -*-

from homevent.statement import main_words, global_words, Statement
from homevent.module import Load,Unload,LoadDir,ModuleExists
from homevent.check import register_condition
from homevent.context import Context
from homevent.parser import read_config
from homevent.run import process_failure
from homevent.reactor import ShutdownHandler,mainloop,shut_down,\
	stop_mainloop
from homevent.logging import TRACE,DEBUG,INFO,WARN,ERROR,PANIC,\
	Logger,register_logger,LogNames
from signal import signal,SIGINT,SIGHUP,SIGQUIT
import sys

from twisted.internet import reactor,defer

global_words.register_statement(Load)
global_words.register_statement(Unload)
global_words.register_statement(LoadDir)
register_condition(ModuleExists)
main_words.register_statement(ShutdownHandler)

from optparse import OptionParser
parser = OptionParser(conflict_handler="resolve")
parser.add_option("-h","--help","-?", action="help",
	help="print this help text")
parser.add_option("-t", "--trace", dest="debuglevel", action="store",
	help="trace level (TRACE,DEBUG,INFO,WARN,ERROR,PANIC,NONE)", default="PANIC")

(opts, args) = parser.parse_args()
if not args:
	print >>sys.stderr,"You need at least one config file!"
	sys.exit(1)

class DoLogger(Logger):
	"""\
		This class implements one particular way to log things.
		"""
	def _log(self,level,txt):
		if txt != ".":
			print >>self.out,LogNames[level]+"> "+txt


if opts.debuglevel != "NONE":
	if opts.debuglevel == opts.debuglevel.upper() and \
			opts.debuglevel in globals():
		register_logger(DoLogger(level=globals()[opts.debuglevel]))
	else:
		raise KeyError("'%s' is not a debug level." % (opts.debuglevel,))

def _readcf():
	d = defer.succeed(None)
	c = Context()
	def rcf(_,fn):
		return read_config(c,fn)
	for f in args:
		d.addCallback(rcf,f)
	d.addErrback(process_failure)

def readcf():
	reactor.callLater(0,_readcf)

signal(SIGINT, lambda a,b: reactor.callLater(0,stop_mainloop))
signal(SIGQUIT,lambda a,b: reactor.callLater(0,shut_down))
signal(SIGHUP, lambda a,b: readcf())

readcf()
mainloop()

