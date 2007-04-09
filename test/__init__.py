#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
import sys

class run_logger(object):
	"""\
		This class checks that the current log matches the stored log.
		"""
	def __init__(self,name):
		try:
			self.data=open(name+"_log")
		except IOError:
			print "ERROR, no log file"
			self.data = None
		self.line=0
		h.register_logger(self)

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
				self.spop(str(event.id)+" "+str(r))
		else:
			self.spop(str(event))
		self.spop(".")

class SayWorker(h.Worker):
	"""A cheap worker which just logs something convenient."""
	prio = 5
	def does_event(self,e):
		return e[0]=="say"
	def run(self,e):
		h.log("The '"+self.name+"' worker is saying: "+" ".join(e[1:]))

class SayMoreWorker(h.SeqWorker):
	"""A WorkSequence-generating worker which logs something twice."""
	prio = 5
	def does_event(self,e):
		return e[0]=="say more"
	def run(self,e):
		w = h.WorkSequence(e,self)
		w.append(SayWorker("TellOne"))
		w.append(SayWorker("TellTwo"))
		return w
