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

from homevent.logging import BaseLogger, TRACE,NONE, log, log_level
from homevent.interpreter import Interpreter
from homevent.parser import parse
from homevent.context import Context
from homevent.times import unixtime,now
from homevent.twist import fix_exception,format_exception,print_exception,TESTING
from homevent.statement import Statement,main_words
from homevent.base import Name
from homevent.reactor import shut_down, mainloop

from cStringIO import StringIO
import sys
import re
import os
import traceback
from time import time
from subprocess import Popen
from twisted.internet import reactor
from tokenize import tok_name

exitcode = 0

log_level("event",TRACE)
log_level("monitor",TRACE)
log_level("fs20",TRACE)
log_level("parser",NONE)
log_level("token",NONE)

startup=now()
realStartup=now(True)
def ixtime(t=None,force=False):
	if t is None:
		t = now(force)
	r = unixtime(t)-unixtime(realStartup if force else startup)
	return "%.1f" % (r,)
def ttime():
	return time()-unixtime(startup)

r_fli = re.compile(r'(:\s+File ").*/([^/]+/[^/]+)", line \d+, in')
r_hex = re.compile(r'object at 0x[0-9a-fA-F]+')

class run_logger(BaseLogger):
	"""\
		This class checks that the current log matches the stored log.
		"""
	def __init__(self,name, dot=True, level=TRACE):
		self.dot=dot
		self.filename = name
		self.name = Name(name)
		self.try_init()
		try:
			self.data=open(os.path.join("real",name),"w")
		except IOError:
			print >>sys.stderr,"ERROR, no log file"
			self.data = sys.stderr
		self.line=0
		super(run_logger,self).__init__(level)

	def try_init(self):
		scp = os.path.join("scripts",self.filename+"_init")
		if not os.path.exists(scp):
			scp = os.path.join("test",scp)
		if os.path.exists(scp):
			job = Popen(scp)
			res = job.wait()
			if res != 0:
				print >>sys.stderr,"Init Script for %s failed: %d" % (self.filename,res)
				sys.exit(0)
			
	def try_exit(self):
		scp = os.path.join("scripts",self.filename+"_exit")
		if not os.path.exists(scp):
			scp = os.path.join("test",scp)
		if os.path.exists(scp):
			sys.stdout.flush()
			sys.stderr.flush()
			self.data.flush()
			job = Popen(scp)
			res = job.wait()
			if res != 0:
				print >>sys.stderr,"Exit Script for %s failed: %d" % (self.filename,res)
				sys.stderr.flush()
				global exitcode
				exitcode = 1

	def _log(self,level, sx):
		self.line += 1
		def rep(m):
			return m.group(1)+m.group(2)+", in"
		if TESTING:
			sx = r_fli.sub(rep,sx)
			sx = r_hex.sub("obj",sx)
		if level is not None:
			print >>self.data, level,sx
		else:
			print >>self.data, sx

	# override using a separate thread
	def _init(self):
		pass
	def _wlog(self,*a):
		self._log(*a)

	def log(self, level, *a):
#		if level is not None and level < self.level:
#			return
		sx=" ".join(unicode(x) for x in a)
		self._log(level,sx)
		if self.dot:
			self._log(None,".")

	def log_event(self, event, level=0):
#		if level < self.level:
#			return

		if TESTING and int(os.environ["HOMEVENT_TEST"]) > 1:
			self._log(None,"@ "+ixtime())
		if hasattr(event,"report"):
			for r in event.report(99):
				self._log(None,unicode(r))
		elif isinstance(event,BaseException):
			for l in format_exception(event).strip('\n').split('\n'):
				self._log(None,l)
		else:
			self._log(None,unicode(event))
		if self.dot:
			self._log(None,".")

	def write(self,s):
		s = s.rstrip()
		if s != "":
			self.log(None,s)

def parse_logger(s,t,c,*x):
	try:
		c = tok_name[c]
	except KeyError:
		pass
	log(TRACE, "%s %s %s %s" % (s,t,c, " ".join(map(str,x))))

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

class ctxdump(Statement):
	name=("dump","context")
	doc="dump the variable context"
	def run(self,ctx,**k):
		event = self.params(ctx)
		print >>sys.stderr,"CTX:",Name(event)
		for s in ctx._report():
			print >>sys.stderr,"   :",s
main_words.register_statement(ctxdump)

def run(name,input, interpreter=Interpreter, logger=None):
	ht = None
	if logger is None:
		ht = run_logger(name,dot=False)
		logger = ht.log
	if isinstance(input,unicode):
		input = input.encode("utf-8")
	input = StringIO(input)

	def _main():
		parse_ctx = Context(filename=name)
		#parse_ctx.logger=parse_logger
		try:
			parse(input, interpreter(Context(out=logwrite(logger))),parse_ctx)
		except Exception as e:
			fix_exception(e)
			print_exception(e,file=sys.stderr)
		finally:
			shut_down()
			if ht is not None:
				ht.try_exit()

	mainloop(_main)

	sys.exit(exitcode)
