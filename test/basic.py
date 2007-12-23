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
import sys
from homevent.logging import TRACE

class SayWorker(h.Worker):
	"""A cheap worker which just logs something convenient."""
	prio = 5
	def does_event(self,e):
		return e[0]=="say"
	def process(self,event,*a,**k):
		h.log(TRACE,"The '"+self.name+"' worker is saying: "+" ".join(event[1:]))

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

from test import run_logger
run_logger("basic")

hello_ev = h.Event(h.Context(), "say","hello")
hello2_ev = h.Event(h.Context(), "say more","greeting")
	
h.register_worker(SayWorker("TellMe"))
h.register_worker(SayMoreWorker("say something"))

def main():
	d = h.process_event(hello_ev)
	d.addCallback(lambda _: h.process_event(hello2_ev))
	d.addBoth(lambda _: h.shut_down())

h.mainloop(main)

