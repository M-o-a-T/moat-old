#!/usr/bin/python
# -*- coding: utf-8 -*-

##
##  Copyright (C) 2007  Matthias Urlichs <matthias@urlichs.de>
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

import homevent as h
from homevent.logging import Logger, TRACE, log
from homevent.interpreter import Interpreter
from homevent.parser import parse
from homevent.context import Context
from homevent.times import unixtime,now
from cStringIO import StringIO
import sys
import re
import os
from twisted.internet import reactor
exitcode = 0

startup=now()
def ixtime(t=None):
	if t is None:
		t = now()
	t = unixtime(t)
	return "%.1f" % (t-unixtime(startup),)

r_fli = re.compile(r'(:\s+File ").*/([^/]+/[^/]+)", line \d+, in')
r_hex = re.compile(r'object at 0x[0-9a-fA-F]+')

class run_logger(Logger):
	"""\
		This class checks that the current log matches the stored log.
		"""
	def __init__(self,name, dot=True, level=TRACE):
		self.dot=dot
		self.name = name
		self.try_init()
		try:
			self.data=open(os.path.join("real",name),"w")
		except IOError:
			print >>sys.stderr,"ERROR, no log file"
			self.data = sys.stderr
		self.line=0
		h.register_logger(self)
		self.level = level

	def try_init(self):
		scp = os.path.join("scripts",self.name+"_init")
		if not os.path.exists(scp):
			scp = os.path.join("test",scp)
		if os.path.exists(scp):
			res = os.spawnlp(os.P_WAIT, scp)
			if res != 0:
				print >>sys.stderr,"Init Script for %s failed: %d" % (self.name,res)
				sys.exit(0)
			
	def try_exit(self):
		scp = os.path.join("scripts",self.name+"_exit")
		if not os.path.exists(scp):
			scp = os.path.join("test",scp)
		if os.path.exists(scp):
			sys.stdout.flush()
			sys.stderr.flush()
			self.data.flush()
			res = os.spawnlp(os.P_WAIT, scp)
			if res != 0:
				print >>sys.stderr,"Exit Script for %s failed: %d" % (self.name,res)
				sys.stderr.flush()
				global exitcode
				exitcode = 1

	def _log(self,level, sx):
		self.line += 1
		def rep(m):
			return m.group(1)+m.group(2)+", in"
		if "HOMEVENT_TEST" in os.environ:
			sx = r_fli.sub(rep,sx)
			sx = r_hex.sub("obj",sx)
		if level is not None:
			print >>self.data, level,sx
		else:
			print >>self.data, sx

	def log(self, level, *a):
		if level is not None and level < self.level:
			return
		sx=" ".join(unicode(x) for x in a)
		self._log(level,sx)
		if self.dot:
			self._log(None,".")

	def log_event(self, event, level=0):
		if level < self.level:
			return

		if "HOMEVENT_TEST" in os.environ and int(os.environ["HOMEVENT_TEST"]) > 1:
			self._log(None,"@ "+ixtime())
		if hasattr(event,"report"):
			for r in event.report(99):
				if not hasattr(event,"id") or isinstance(event,(h.logging.log_run,h.logging.log_created)):
					self._log(None,unicode(r))
				else:
					self._log(None,str(event.id)+" "+unicode(r))
		else:
			self._log(None,unicode(event))
		if self.dot:
			self._log(None,".")

	def write(self,s):
		s = s.rstrip()
		if s != "":
			self.log(None,s)

def parse_logger(s,t,c,*x):
	pass
	#if t == COMMENT:
	#log(TRACE, "%s %s %s %s" % tuple(map(repr,(s,t,c,x))))

class logwrite(object):
	def __init__(self,log):
		self.log = log
		self.buf = ""
	def write(self,data):
		self.buf += data
		if self.buf[-1] == "\n":
			if len(self.buf) > 1:
				for l in self.buf.rstrip("\n").split("\n"):
					self.log(None,l)
			self.buf=""
	def flush(self):
		if self.buf:
			l = self.buf
			self.buf = ""
			self.log(None,l)
		pass

def run(name,input, interpreter=Interpreter, logger=None):
	ht = None
	if logger is None:
		ht = run_logger(name,dot=False)
		logger = ht.log
	if isinstance(input,unicode):
		input = input.encode("utf-8")
	input = StringIO(input)

	def _main():
		d = parse(input, interpreter(Context(out=logwrite(logger))),Context(logger=parse_logger))
		d.addErrback(lambda _: _.printTraceback())
		d.addBoth(lambda _: h.shut_down())
		if ht is not None: d.addBoth(lambda _: ht.try_exit())

	h.mainloop(_main)

	sys.exit(exitcode)
