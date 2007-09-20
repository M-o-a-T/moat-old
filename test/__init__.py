#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.logging import Logger, TRACE, log
from homevent.interpreter import Interpreter
from homevent.parser import parse
from homevent.context import Context
from cStringIO import StringIO
import sys
import re
import os
from twisted.internet import reactor

r_fli = re.compile(r'(:\s+File ").*/([^/]+/[^/]+)", line \d+, in')
r_hex = re.compile(r'object at 0x[0-9a-fA-F]+')

class run_logger(Logger):
	"""\
		This class checks that the current log matches the stored log.
		"""
	def __init__(self,name, dot=True, level=TRACE):
		self.dot=dot
		try:
			self.data=open(os.path.join("real",name),"w")
		except IOError:
			print >>sys.stderr,"ERROR, no log file"
			self.data = sys.stderr
		self.line=0
		h.register_logger(self)
		self.level = level

	def _log(self,level, sx):
		self.line += 1
		def rep(m):
			return m.group(1)+m.group(2)+", in"
		sx = r_fli.sub(rep,sx)
		sx = r_hex.sub("obj",sx)
		if level is not None:
			print >>self.data, level,sx
		else:
			print >>self.data, sx

	def log(self, level, *a):
		if level is not None and level < self.level:
			return
		sx=" ".join(str(x) for x in a)
		self._log(level,sx)
		if self.dot:
			self._log(None,".")

	def log_event(self, event, level=0):
		if level < self.level:
			return
		if hasattr(event,"report"):
			for r in event.report(99):
				if not hasattr(event,"id") or isinstance(event,(h.logging.log_run,h.logging.log_created)):
					self._log(None,str(r))
				else:
					self._log(None,str(event.id)+" "+str(r))
		else:
			self._log(None,str(event))
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
	if logger is None:
		logger = run_logger(name,dot=False).log
	input = StringIO(input)

	def _main():
		d = parse(input, interpreter(Context(out=logwrite(logger))),Context(logger=parse_logger))
		d.addErrback(lambda _: _.printTraceback())
		d.addBoth(lambda _: h.shut_down())

	h.mainloop(_main)

