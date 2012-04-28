#!/usr/bin/python
# -*- coding: utf-8 -*-

##
##  Copyright © 2007, Matthias Urlichs <matthias@urlichs.de>
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

import sys
from homevent.logging import TRACE
from homevent.worker import Worker,SeqWorker,WorkSequence
from homevent.event import Event
from homevent.context import Context
from homevent.logging import log
from homevent.run import register_worker,process_event
from homevent.reactor import shut_down,mainloop

class SayWorker(Worker):
	"""A cheap worker which just logs something convenient."""
	prio = 5
	def does_event(self,e):
		return e[0]=="say"
	def process(self,event=None,**k):
		super(SayWorker,self).process(event=event,**k)
		if event:
			log(TRACE,"The '"+self.name+"' worker is saying: "+" ".join(event[1:]))
		else:
			log(TRACE,"The '"+self.name+"' worker is saying: ???")

class SayMoreWorker(SeqWorker):
	"""A WorkSequence-generating worker which logs something twice."""
	prio = 5
	def does_event(self,e):
		return e[0]=="say more"
	def process(self,event=None,**k):
		super(SayMoreWorker,self).process(event=event,**k)
		w = WorkSequence(event,self)
		w.append(SayWorker("TellOne"))
		w.append(SayWorker("TellTwo"))
		return w

from test import run_logger
run_logger("basic")

hello_ev = Event(Context(), "say","hello")
hello2_ev = Event(Context(), "say more","greeting")
	
register_worker(SayWorker("TellMe"))
register_worker(SayMoreWorker("say something"))

def main():
	try:
		process_event(hello_ev)
		process_event(hello2_ev)
	finally:
		shut_down()

mainloop(main)

