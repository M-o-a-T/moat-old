#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
from homevent.logging import Logger, TRACE
import sys
import re
from twisted.internet import reactor

r_fli = re.compile(r'(:\s+File ").*/([^/]+/[^/]+)", line \d+, in')
r_hex = re.compile(r'object at 0x[0-9a-fA-F]+')

class run_logger(Logger):
	"""\
		This class checks that the current log matches the stored log.
		"""
	def __init__(self,name, dot=True):
		self.dot=dot
		try:
			self.data=open(name+"_log")
		except IOError:
			print >>sys.stderr,"ERROR, no log file"
			self.data = None
		self.line=0
		h.register_logger(self)
		self.level = TRACE

	def __del__(self):
		if self.data:
			sp = self.data.readline()
			if sp:
				print "ERROR, line",self.line,"-- more data in log"
		
	def _log(self,sx):
		self.line += 1
		def rep(m):
			return m.group(1)+m.group(2)+", in"
		sx = r_fli.sub(rep,sx)
		sx = r_hex.sub("obj",sx)
		if not self.data:
			print sx
			return
		sp = self.data.readline().rstrip("\n")
		if sp.rstrip() != sx.rstrip():
			print "ERROR, line",self.line
			print "expect:",repr(sp)
			print "got   :",repr(sx)
			self.data = None

	def log(self, *a):
		sx=" ".join(str(x) for x in a)
		self._log(sx)
		if self.dot:
			self._log(".")

	def log_event(self, event, level=0):
		if hasattr(event,"report"):
			for r in event.report(99):
				if not hasattr(event,"id") or isinstance(event,(h.logging.log_run,h.logging.log_created)):
					self._log(str(r))
				else:
					self._log(str(event.id)+" "+str(r))
		else:
			self._log(str(event))
		if self.dot:
			self._log(".")

	def write(self,s):
		s = s.rstrip()
		if s != "":
			self.log(s)

class SayWorker(h.Worker):
	"""A cheap worker which just logs something convenient."""
	prio = 5
	def does_event(self,e):
		return e[0]=="say"
	def process(self,event,*a,**k):
		h.log("The '"+self.name+"' worker is saying: "+" ".join(event[1:]))

class SayMoreWorker(h.SeqWorker):
	"""A WorkSequence-generating worker which logs something twice."""
	prio = 5
	def does_event(self,e):
		return e[0]=="say more"
	def process(self,event,*a,**k):
		w = h.WorkSequence(event,self)
		w.append(SayWorker("TellOne"))
		w.append(SayWorker("TellTwo"))
		return w

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

