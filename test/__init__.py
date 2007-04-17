#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
import sys
from twisted.internet import reactor

class run_logger(object):
	"""\
		This class checks that the current log matches the stored log.
		"""
	def __init__(self,name, dot=True):
		self.dot=dot
		try:
			self.data=open(name+"_log")
		except IOError:
			print "ERROR, no log file"
			self.data = None
		self.line=0
		h.register_logger(self)

	def __del__(self):
		if self.data:
			sp = self.data.readline()
			if sp:
				print "ERROR, line",self.line,"-- more data in log"
		
	def spop(self,sx):
		self.line += 1
		if not self.data:
			print sx
			return
		sp = self.data.readline().rstrip("\n")
		if sp != sx:
			print "ERROR, line",self.line
			print "expect:",sp
			print "got   :"
			print sx
			self.data = None

	def log(self, event, level=0):
		global s
		if hasattr(event,"report"):
			for r in event.report(99):
				if not hasattr(event,"id") or isinstance(event,(h.logging.log_run,h.logging.log_created)):
					self.spop(str(r))
				else:
					self.spop(str(event.id)+" "+str(r))
		else:
			self.spop(str(event))
		if self.dot:
			self.spop(".")
	def write(self,s):
		s = s.rstrip()
		if s != "":
			self.log(s)

class SayWorker(h.Worker):
	"""A cheap worker which just logs something convenient."""
	prio = 5
	def does_event(self,e):
		return e[0]=="say"
	def run(self,event,*a,**k):
		h.log("The '"+self.name+"' worker is saying: "+" ".join(event[1:]))

class SayMoreWorker(h.SeqWorker):
	"""A WorkSequence-generating worker which logs something twice."""
	prio = 5
	def does_event(self,e):
		return e[0]=="say more"
	def run(self,event,*a,**k):
		w = h.WorkSequence(event,self)
		w.append(SayWorker("TellOne"))
		w.append(SayWorker("TellTwo"))
		return w
