#!/usr/bin/python
# -*- coding: utf-8 -*-

import homevent as h
import sys

from test import mainloop, run_logger,SayWorker,SayMoreWorker
run_logger("basic")

hello_ev = h.Event("say","hello")
hello2_ev = h.Event("say more","greeting")
	
h.register_worker(SayWorker("TellMe"))
h.register_worker(SayMoreWorker("say something"))

def main():
	h.process_event(hello_ev)
	h.process_event(hello2_ev)

mainloop(main)

