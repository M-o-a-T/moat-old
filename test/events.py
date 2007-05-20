#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
import homevent.parser as hp
from homevent.context import Context
from homevent.reactor import ShutdownHandler
from homevent.module import load_module
from StringIO import StringIO
from test import run_logger

logger = run_logger("events",dot=False)
log = logger.log

input = StringIO("""\
trigger foo
wait for 1m -90s 0.5min +.5s
trigger bar
""")

hp.main_words.register_statement(ShutdownHandler)
load_module("events").load()

from tokenize import COMMENT

def logger(s,t,c,*x):
	pass
	#if t == COMMENT:
	#	log(c.rstrip())

class logwrite(object):
	def __init__(self,log):
		self.log = log
		self.buf = ""
	def write(self,data):
		self.buf += data
		if self.buf[-1] == "\n":
			if len(self.buf) > 1:
				for l in self.buf.rstrip("\n").split("\n"):
					self.log(l)
			self.buf=""

def main():
	d = hp.parse(input, hp.Interpreter(Context(out=logwrite(log))), Context(logger=logger)) # , out=log)
	d.addErrback(lambda _: _.printTraceback())
	d.addBoth(lambda _: h.shut_down())

h.mainloop(main)

