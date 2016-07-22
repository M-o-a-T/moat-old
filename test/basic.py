#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2016 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
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
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

import sys
from moat.logging import TRACE
from moat.worker import Worker,SeqWorker,WorkSequence
from moat.event import Event
from moat.context import Context
from moat.logging import log
from moat.run import register_worker,process_event
from moat.reactor import shut_down,mainloop

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

