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

from homevent.interpreter import InteractiveInterpreter,Interpreter
from homevent.parser import parse
from homevent.statement import main_words, global_words
from homevent.check import register_condition
from homevent.module import load_module, Load,LoadDir
from homevent.reactor import ShutdownHandler,mainloop,shut_down
from homevent.context import Context
from homevent.twist import callLater,fix_exception

from tokenize import tok_name
import os,sys

main_words.register_statement(Load)
main_words.register_statement(LoadDir)
main_words.register_statement(ShutdownHandler)

load_module("help")
load_module("data")
load_module("file")
load_module("path")
load_module("ifelse")

syms = {}
def parse_logger(t,*x):
	x=list(x)
	try:
		x[1] = tok_name[x[1]]
	except KeyError:
		pass
	print t+":"+" ".join(str(d) for d in x)

def reporter(err):
	print "Error:",err
	
def looper():
	while True:
		print "L"
		sleep(1)

def ready():
	c=Context()
	for f in sys.argv[1:]:
		parse(f, ctx=c)
	
	#c.logger=parse_logger
	if os.isatty(0):
		i = InteractiveInterpreter
	else:
		i = Interpreter
	print """Ready. Type «help» if you don't know what to do."""
	try:
		parse(sys.stdin, interpreter=i, ctx=c)
	except Exception as e:
		fix_exception(e)
		reporter(e)
	shut_down()

from gevent import spawn,sleep
#spawn(looper)
callLater(False,0.1,ready)
mainloop()

