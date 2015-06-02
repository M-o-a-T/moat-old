#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2015 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
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
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

from moat import patch;patch()
from moat.interpreter import InteractiveInterpreter,Interpreter
from moat.parser import parse
from moat.statement import main_words, global_words
from moat.check import register_condition
from moat.module import load_module, Load,LoadDir
from moat.reactor import ShutdownHandler,mainloop,shut_down
from moat.context import Context
from moat.twist import callLater,fix_exception
from moat.logging import log_level,NONE

from tokenize import tok_name
import os,sys

main_words.register_statement(Load)
main_words.register_statement(LoadDir)
main_words.register_statement(ShutdownHandler)

log_level("token",NONE)
log_level("parser",NONE)

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
	print(t+":"+" ".join(str(d) for d in x))

def reporter(err):
	print("Error:",err)
	
def looper():
	while True:
		print("L")
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
	print("""Ready. Type «help» if you don't know what to do.""")
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

