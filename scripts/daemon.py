#!/usr/bin/python
# -*- coding: utf-8 -*-

##
##  Copyright © 2007-2012, Matthias Urlichs <matthias@urlichs.de>
##
##  This program is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License (included; see the file LICENSE)
##  for more details.
##

import sys; sys.excepthook = None; del sys

from homevent.statement import main_words, global_words, Statement, \
	DoNothingHandler
from homevent.module import Load,LoadDir,load_module
from homevent.check import register_condition
from homevent.context import Context
from homevent.parser import parse
from homevent.run import process_failure
from homevent.twist import track_errors, fix_exception
from homevent.reactor import ShutdownHandler,mainloop,shut_down,\
	stop_mainloop
from homevent.logging import TRACE,DEBUG,INFO,WARN,ERROR,PANIC,\
	Logger,LogNames, log_level
from signal import signal,SIGINT,SIGHUP,SIGQUIT
import sys
import os
import gevent

from twisted.internet import reactor

main_words.register_statement(Load)
main_words.register_statement(LoadDir)
main_words.register_statement(ShutdownHandler)
main_words.register_statement(DoNothingHandler)
load_module("ifelse")

from optparse import OptionParser
parser = OptionParser(conflict_handler="resolve")
parser.add_option("-h","--help","-?", action="help",
	help="print this help text")
parser.add_option("-t", "--trace", dest="debuglevel", action="store",
	help="trace level (TRACE,DEBUG,INFO,WARN,ERROR,PANIC,NONE)", default="PANIC")
parser.add_option("-s", "--stack", dest="stack", action="store_true",
	help="HomEvenT errors are logged with Python stack traces")
parser.add_option("-p", "--pidfile", dest="pidfile", action="store",
	help="file to write our PID to")

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
	for level in opts.debuglevel.split(","):
		if "=" in level:
			subsys,level = level.split("=")
			log_level(subsys, globals()[level])
		elif level == level.upper() and level in globals():
			DoLogger(level=globals()[level])
		else:
			raise KeyError("'%s' is not a debug level." % (level,))

track_errors(opts.stack)

if opts.pidfile:
	pid = open(opts.pidfile,"w")
	print >>pid, os.getpid()
	pid.close()

def _readcf():
	c = Context()
	try:
		for f in args:
			parse(f,ctx=c)
	except Exception as e:
		fix_exception(e)
		process_failure(e)
		shut_down()

reading = None
def readcf():
	global reading
	if reading:
		return
	reading = gevent.spawn(_readcf)
	def read_done(_):
		global reading
		reading = False
	reading.link(read_done)

signal(SIGINT, lambda a,b: gevent.spawn(stop_mainloop))
signal(SIGQUIT,lambda a,b: gevent.spawn(shut_down))
signal(SIGHUP, lambda a,b: readcf())

readcf()
mainloop()

