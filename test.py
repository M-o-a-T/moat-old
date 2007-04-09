#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
import sys

s=open("test_log")
snum=0

def spop(sx):
	global snum
	snum += 1
	sp = s.readline().rstrip("\n")
	if sp != sx:
		print "ERROR, line",snum
		print "expect:",sp
		print "got   :",sx
		sys.exit(1)

class TestLogger(object):
	"""\
		This class implements one particular way to log things.
		"""
	def log(self, event, level=0):
		global s
		if hasattr(event,"report"):
			for r in event.report(99):
				spop(str(event.id)+" "+str(r))
		else:
			spop(str(event))
		spop(".")
h.register_logger(TestLogger())

startup_ev = h.Event("startup")
hello_ev = h.Event("say","hello")
hello2_ev = h.Event("say more","greeting")
shutdown_ev = h.Event("shutdown")
	
class SayWorker(h.Worker):
	prio = 5
	def does_event(self,e):
		return e[0]=="say"
	def run(self,e):
		h.log("The '"+self.name+"' worker is saying: "+" ".join(e[1:]))

h.register_worker(SayWorker("TellMe"))

class SayMoreWorker(h.SeqWorker):
	prio = 5
	def does_event(self,e):
		return e[0]=="say more"
	def run(self,e):
		w = h.WorkSequence(e,self)
		w.append(SayWorker("TellOne"))
		w.append(SayWorker("TellTwo"))
		return w

h.register_worker(SayMoreWorker("say something"))

h.process_event(startup_ev)

h.process_event(hello_ev)

e = h.collect_event(hello2_ev)
h.log(e)
e.run(hello2_ev)

h.process_event(shutdown_ev)

