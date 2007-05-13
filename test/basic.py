#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
import sys

from test import run_logger,SayWorker,SayMoreWorker
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

